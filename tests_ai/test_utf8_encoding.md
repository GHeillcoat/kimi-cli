# UTF-8 编码和解码

## 显式 UTF-8 编码

**范围**

`src/kimi_cli/` 目录下的所有 Python 文件。

**要求**

在读取或写入文件、编码或解码文本时，必须显式指定 `encoding="utf-8"`。

<examples>
```python
text.encode()  # 不正确：依赖默认编码
path.read_text(encoding="utf-8")  # 正确：显式指定 UTF-8
with open(file, "r", encoding="utf-8") as f:  # 正确
with aiofiles.open(file, "w", encoding="utf-8") as f:  # 正确
process.output.decode() # 不正确：依赖默认编码
```
</examples>
