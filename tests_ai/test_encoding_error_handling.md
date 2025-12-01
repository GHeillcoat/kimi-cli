# 解码错误处理

## 解码用户提供内容时的错误处理

**范围**

`src/kimi_cli/tools/` 目录下的所有 Python 文件，除了 `load_desc` 函数。

**要求**

在解码用户提供的内容时，例如读取文件、解码子进程输出等，必须指定 `errors="replace"`，以避免由于格式错误的 UTF-8 序列导致的运行时崩溃。

写入文件和将 Python 字符串编码为字节不需要 `errors="replace"`。

<examples>
```python
subprocess.run(..., encoding="utf-8", errors="replace")  # 正确：替换不可解码的字节
aiofiles.open(..., encoding="utf-8", errors="replace")  # 正确：替换不可解码的字节
```
</examples>
