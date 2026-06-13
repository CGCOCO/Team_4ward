import os
from pathlib import Path

# 사진 폴더 경로
folder = Path(r"C:\develop\Team_4ward\scripts\2")

# 이미지 파일만 가져오기
image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
files = sorted([f for f in folder.iterdir() if f.suffix.lower() in image_extensions])

start_num = 34

# 이름 충돌 방지를 위해 임시 이름으로 변경
for i, file in enumerate(files):
    temp_name = folder / f"temp_{i}{file.suffix}"
    file.rename(temp_name)

temp_files = sorted(folder.glob("temp_*"))

# 최종 이름으로 변경
for i, file in enumerate(temp_files):
    new_name = folder / f"{start_num + i}{file.suffix}"
    file.rename(new_name)

print("이름 변경 완료!")