import opencc

converter = opencc.OpenCC("t2s.json")  # 繁体 → 简体
print(converter.convert("國風·周南·關雎"))