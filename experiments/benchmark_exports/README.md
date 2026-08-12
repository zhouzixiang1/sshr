# Benchmark exports

BLIF、PLA、truth JSON 和第三方工具交换文件属于可再生成产物，默认不进入 Git。

需要时使用项目 runner 或 `submission/export_benchmarks.py` 重建，并在独立
artifact 目录保存 manifest、工具版本、命令和 SHA-256。
