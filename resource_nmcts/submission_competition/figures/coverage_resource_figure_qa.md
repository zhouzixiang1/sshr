# F5 图件 QA 记录

- 后端独占：Python/matplotlib；预览缩放由 Python/Pillow 完成。
- SVG：`<text>` 节点 200 个，嵌入 raster `<image>` 0 个；可编辑文本检查通过。
- PDF：1 页，183.00 mm × 110.00 mm；双栏尺寸检查通过。
- PNG：4322 × 2598 px，600 dpi 输出尺寸检查通过。
- 数据不变量：360 planned、360 verified、0 synthesis timeout；0 mismatch、0 coupling violation、0 unsupported instruction、0 memory guard。
- 遥测边界：n=100 v3 records；median 26.55%、p95 29.8%、max 30.7%；70% 为软件软阈值。
- 设备措辞：图中只写 `Qiskit Aer available_devices = CPU`，不声称 GPU Aer。
- 视觉检查：已逐一检查 PNG 与 PDF QA preview；20×6 矩阵标签可辨，右侧数字卡片无重叠，资源分位数、70% 软阈值与三条证据边界均未遮挡或越界。
- 灰度/无色容错：覆盖格内同时使用 `3/3` 与 `0/3 TO`；超时区另带橙色与纹理，资源状态另用圆点/三角形，结论不依赖颜色单独传意。
