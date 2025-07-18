
# PapaKiki PSP - Script Dumper & Repacker

This toolset was created by gopicolo for you to extract and reinsert text from `.bin` script files in the PSP game titled:

**Game demo, Papa no Iu Koto o Kikinasai!**

## 📁 Folder Structure

```
PapaKiki-PSP-Tool/
├── dump.py
├── repack.py
├── input/         # Original .bin files
├── output/        # Extracted or edited text files
└── modified/      # Final repacked .bin files
```

---
These script files are located in:

```
/PSP_GAME/USRDIR/Script/
```

It consists of two Python scripts:

- `dump.py`: Extracts text from binary `.bin` files into editable `.txt` files.
- `repack.py`: Reinserts modified text from `.txt` files back into `.bin` files, updating all necessary pointers.

---

## 📤 How to Extract Text

1. Place all `.bin` files you want to extract in the `input/` folder.
2. Run:

   ```bash
   python dump.py
   ```

3. Extracted `.txt` files will be saved to the `output/` folder.

Each extracted file will contain blocks like:

```text
# POINTER BLOCK @ 0x01D9 (Text at 0x29D0)
「その頃、まだ高校生だった姉さんは
　誰の助けも借りずに
　たった一人で俺を育ててくれた」
```

- You can freely edit the lines after the pointer block headers.

---

## 📥 How to Repack

1. Place your edited `_extracted.txt` files back into the `output/` folder (keeping the same name).
2. Make sure the corresponding original `.bin` files remain in `input/`.
3. Run:

   ```bash
   python repack.py
   ```

4. Modified `.bin` files will be created in the `modified/` folder.

---

## 📌 Notes

- Encoding: **Shift-JIS**
- Pointer format: 2-byte Little Endian (some rare cases might use 4-byte, but 2-byte is standard).
- Terminators automatically handled: supports various patterns (`\x00`, `\x00\x00`, `\x0A\x00\x00`, etc.)
- Multiple pointers per string are supported and updated correctly during repack.

---

## 🔧 Requirements

- Python 3.7+
- No external libraries needed (only built-in modules are used)

---
