import os
import struct
import re
from pathlib import Path

# --- CONFIGURAÇÃO ---
ORIGINAL_BIN_DIR = "input"
MODIFIED_TXT_DIR = "output"
REPACKED_BIN_DIR = "modified"

TEXT_ENCODING = "shift_jis"
TERMINATOR = b'\x00'

def parse_extracted_file(txt_path: Path):
    """
    MODIFICADO: Analisa o arquivo de texto e extrai a lista de ponteiros para cada bloco.
    """
    blocks = []
    with txt_path.open("r", encoding="utf-8") as f:
        content = f.read()

    # Regex MODIFICADO: Captura o grupo inteiro de ponteiros como uma string.
    pattern = re.compile(
        r"# POINTER BLOCK @ (.*?) \(Text at 0x([0-9A-Fa-f]{4})\)\n(.*?)\n\n",
        re.DOTALL
    )

    for match in pattern.finditer(content):
        # ptrs_str pode ser "???" ou "0x1234, 0x5678, ..."
        ptrs_str, text_off_str, text_content = match.groups()

        ptr_locs = []
        if ptrs_str.strip() != "???":
            # Divide a string pela vírgula, remove espaços e converte de hex para int
            hex_values = ptrs_str.split(',')
            ptr_locs = [int(p.strip(), 16) for p in hex_values]
        
        text_off = int(text_off_str, 16)
        text = text_content.strip()

        blocks.append({
            "ptr_locs": ptr_locs, # MODIFICADO: Agora é uma lista 'ptr_locs'
            "text_off": text_off,
            "text": text
        })
    
    return blocks

def repack_file(txt_file_path: Path):
    base_name = txt_file_path.stem.replace("_extracted", "")
    original_bin_path = Path(ORIGINAL_BIN_DIR) / (base_name + ".bin")
    repacked_bin_path = Path(REPACKED_BIN_DIR) / (base_name + ".bin")

    if not original_bin_path.exists():
        print(f"[AVISO] Arquivo bin original não encontrado para {txt_file_path.name}. Pulando.")
        return

    try:
        text_blocks = parse_extracted_file(txt_file_path)
        if not text_blocks:
            print(f"[AVISO] Nenhum bloco de texto encontrado em {txt_file_path.name}. Pulando.")
            return

        with original_bin_path.open("rb") as f:
            bin_data = bytearray(f.read())

        new_text_start_offset = min(block['text_off'] for block in text_blocks)
        current_text_offset = new_text_start_offset
        new_text_blob = bytearray()

        for block in text_blocks:
            ptr_locations = block['ptr_locs'] # É uma lista!
            encoded_text = block['text'].encode(TEXT_ENCODING)
            
            # O novo valor do ponteiro é o offset atual onde o texto será escrito
            new_pointer_value = current_text_offset
            
            # Se a lista de ponteiros não estiver vazia, atualiza CADA um.
            if ptr_locations:
                pointer_bytes = struct.pack("<H", new_pointer_value)
                # MODIFICADO: Itera sobre cada localização de ponteiro e a atualiza.
                for loc in ptr_locations:
                    bin_data[loc : loc + 2] = pointer_bytes

            new_text_blob.extend(encoded_text)
            new_text_blob.extend(TERMINATOR)
            current_text_offset = new_text_start_offset + len(new_text_blob)

        final_data = bin_data[:new_text_start_offset]
        final_data.extend(new_text_blob)

        with repacked_bin_path.open("wb") as f:
            f.write(final_data)
            
        print(f"[OK] {original_bin_path.name} reempacotado com sucesso para {repacked_bin_path.name}")

    except Exception as e:
        print(f"[ERRO] Falha ao reempacotar {txt_file_path.name}: {e}")
        import traceback
        traceback.print_exc()

def main():
    if not Path(ORIGINAL_BIN_DIR).exists():
        print(f"ERRO: A pasta de binários originais '{ORIGINAL_BIN_DIR}' não foi encontrada.")
        return
    if not Path(MODIFIED_TXT_DIR).exists():
        print(f"ERRO: A pasta de textos modificados '{MODIFIED_TXT_DIR}' não foi encontrada.")
        return
        
    os.makedirs(REPACKED_BIN_DIR, exist_ok=True)

    modified_files = list(Path(MODIFIED_TXT_DIR).glob("*_extracted.txt"))
    if not modified_files:
        print(f"Nenhum arquivo _extracted.txt encontrado na pasta '{MODIFIED_TXT_DIR}'.")
        return
        
    print(f"Encontrados {len(modified_files)} arquivos de texto para reempacotar...")
    for file in modified_files:
        repack_file(file)
    print("Processamento concluído.")

if __name__ == "__main__":
    main()