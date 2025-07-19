import os
import struct
import string
from pathlib import Path
from collections import defaultdict

# --- CONFIGURAÇÃO ---
INPUT_DIR = "input"
OUTPUT_DIR = "output"
TEXT_ENCODING = "shift_jis"
POINTER_TABLE_CANDIDATES = [0x35, 0x49, 0x21, 0x7B, 0x85, 0x80, 0xDF, 0x2BA, 0x120]

TERMINATORS = [
    b'\x00', b'\x00\x00', b'\x00\x00\x00', b'\x00\x00\x00\x00',
    b'\x0A\x00', b'\x0A\x00\x00', b'\x0A\x00\x00\x00', b'\x0A\x00\x00\x00\x00',
]

def find_terminator(data, start_offset):
    max_len = len(data)
    for i in range(start_offset, max_len):
        for term in TERMINATORS:
            if i + len(term) <= max_len and data[i:i+len(term)] == term:
                raw_text = data[start_offset:i]
                next_pos = i + len(term)
                while next_pos < max_len and data[next_pos] == 0x00:
                    next_pos += 1
                return raw_text, next_pos
    return data[start_offset:max_len], max_len

def find_pointer_locations(bin_data, text_offsets):
    pointer_locations = defaultdict(list)
    data_len = len(bin_data)

    for i in range(data_len - 4):
        val_2 = struct.unpack_from("<H", bin_data, i)[0]
        val_4 = struct.unpack_from("<I", bin_data, i)[0]

        if val_2 in text_offsets:
            pointer_locations[val_2].append(i)
        elif val_4 in text_offsets:
            pointer_locations[val_4].append(i)

    return pointer_locations

def get_first_valid_pointer_offset(bin_data):
    data_len = len(bin_data)
    for candidate in POINTER_TABLE_CANDIDATES:
        try:
            val = struct.unpack_from("<H", bin_data, candidate)[0]
            if 0 < val < data_len:
                print(f"[DEBUG] Ponteiro inicial válido encontrado em 0x{candidate:04X}: 0x{val:04X}")
                return val, candidate
        except (struct.error, IndexError):
            continue
    return None, None

def is_valid_text(text: str):
    return len(text.strip()) >= 4 and all(c in string.printable for c in text)

def find_valid_start_index(blocks):
    for i in range(len(blocks) - 1):
        b1 = blocks[i]
        b2 = blocks[i + 1]
        if b1["ptr_locs"] and is_valid_text(b1["text"]) and b2["ptr_locs"] and is_valid_text(b2["text"]):
            return i
    return 0

def filter_cpt_blocks(blocks):
    """
    Se encontrar uma string com 'CPT' ou 'SCPT',
    apagar essa string e todas as que vêm depois,
    até achar uma string com pelo menos 7 caracteres.
    Se não achar nenhuma string com >=7 caracteres depois,
    retorna lista vazia e flag indicando que tudo deve ser removido.
    """
    found_trigger = False
    filtered = []
    skip_mode = False
    valid_found_after_trigger = False

    for block in blocks:
        text = block["text"]
        if not found_trigger:
            if "CPT" in text or "SCPT" in text:
                found_trigger = True
                skip_mode = True
                continue
            else:
                filtered.append(block)
        else:
            if skip_mode:
                if len(text.strip()) >= 5:
                    skip_mode = False
                    valid_found_after_trigger = True
                    filtered.append(block)
                else:
                    continue
            else:
                filtered.append(block)

    if found_trigger and not valid_found_after_trigger:
        return [], False

    return filtered, True

def process_file(file_path: Path):
    try:
        with file_path.open("rb") as f:
            bin_data = f.read()

        data_len = len(bin_data)
        first_text_offset, _ = get_first_valid_pointer_offset(bin_data)
        if first_text_offset is None:
            print(f"[AVISO] Nenhum ponteiro válido encontrado em {file_path.name}.")
            return

        final_blocks = []
        current_offset = first_text_offset
        extracted_offsets = set()

        while current_offset < data_len:
            if current_offset in extracted_offsets:
                break

            raw_str, next_pos = find_terminator(bin_data, current_offset)

            if not raw_str:
                if next_pos <= current_offset:
                    break
                current_offset = next_pos
                continue

            try:
                decoded_str = raw_str.decode(TEXT_ENCODING).strip()
                if decoded_str:
                    final_blocks.append({
                        "ptr_locs": [],
                        "text_off": current_offset,
                        "text": decoded_str
                    })
                    extracted_offsets.add(current_offset)
            except UnicodeDecodeError:
                pass

            if next_pos <= current_offset:
                break
            current_offset = next_pos

        if not final_blocks:
            print(f"[AVISO] Nenhuma string extraída de {file_path.name}")
            return

        # Aplica o filtro CPT solicitado:
        filtered_blocks, valid = filter_cpt_blocks(final_blocks)

        if not valid:
            print(f"[AVISO] O script em {file_path.name} contém 'CPT' mas nenhuma string válida após o filtro. Todo o texto será removido.")
            return  # Não salva o arquivo nem processa mais

        text_offset_set = set(block["text_off"] for block in filtered_blocks)
        pointer_map = find_pointer_locations(bin_data, text_offset_set)

        for block in filtered_blocks:
            off = block["text_off"]
            block["ptr_locs"] = pointer_map.get(off, [])

        has_unknown_pointers = any(not block["ptr_locs"] for block in filtered_blocks)

        if has_unknown_pointers:
            start_idx = find_valid_start_index(filtered_blocks)
            filtered_blocks = filtered_blocks[start_idx:]

        if not filtered_blocks:
            print(f"[AVISO] Todos os blocos foram filtrados de {file_path.name}")
            return

        output_path = Path(OUTPUT_DIR) / (file_path.stem + "_extracted.txt")
        with output_path.open("w", encoding="utf-8") as out:
            for block in filtered_blocks:
                if not block["ptr_locs"]:
                    ptr_str = "???"
                else:
                    sorted_locs = sorted(block["ptr_locs"])
                    ptr_str = ", ".join([f"0x{loc:04X}" for loc in sorted_locs])
                out.write(f"# POINTER BLOCK @ {ptr_str} (Text at 0x{block['text_off']:X})\n")
                out.write(f"{block['text']}\n\n")

        print(f"[OK] {file_path.name} extraído com sucesso. {len(filtered_blocks)} strings mantidas.")

    except Exception as e:
        print(f"[ERRO] Falha ao processar {file_path.name}: {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    input_files = list(Path(INPUT_DIR).glob("*.bin"))
    if not input_files:
        print(f"Nenhum arquivo .bin encontrado na pasta '{INPUT_DIR}'.")
        return
    print(f"Encontrados {len(input_files)} arquivos para processar...")
    for file in input_files:
        process_file(file)
    print("Processamento concluído.")

if __name__ == "__main__":
    main()
