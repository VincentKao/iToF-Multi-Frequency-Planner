# iToF 多頻率規劃與 Phase Unwrapping 分析平台

## 專案背景

間接式飛行時間感測器（Indirect Time-of-Flight, iToF）透過量測發射光與反射光之間的相位差（Phase Shift）來估算目標距離。

其基本模型如下：

$$
d = \frac{c}{4\pi f}\phi
$$

其中：

- d：目標距離
- c：光速
- f：調制頻率（Modulation Frequency）
- φ：量測到的相位差

---

## 核心問題：Phase Ambiguity

由於相位只能量測：

$$
\phi \in [0, 2\pi)
$$

因此：

$$
\phi =
\left(
\frac{4\pi f d}{c}
\right)
\bmod 2\pi
$$

實際上感測器只能得到：

$$
d \bmod \frac{c}{2f}
$$

因此真實距離可能為：

$$
d =
d_0 + k\frac{c}{2f}
$$

其中：

- k 為整數

換句話說：

```text
同一個相位值
可能對應多個真實距離
```

這稱為：

- Phase Wrapping
- Distance Ambiguity

這不是系統誤差，而是 iToF 量測模型本身的數學特性。

---

## 範例

假設：

f = 80 MHz

則：

$$
R = \frac{c}{2f}
$$

得到：

$$
R = 1.875m
$$

若量測到某個相位值：

可能代表：

```text
0.30 m
2.175 m
4.050 m
5.925 m
...
```

單一頻率無法判斷哪一個才是真實距離。

---

# 多頻率解法（Multi-Frequency ToF）

為了解決 ambiguity 問題，系統會使用多組 modulation frequency：

```text
f1
f2
f3
...
```

例如：

```text
20 MHz
60 MHz
100 MHz
```

每個頻率分別得到：

```text
φ1
φ2
φ3
```

最後利用所有 phase 條件共同求解真實距離。

本質上類似：

- 中國剩餘定理（CRT）
- 多重模方程求解
- 帶雜訊條件下的整數解搜尋

---

# 專案目標

建立一套可視化工具，用於：

1. iToF 頻率規劃（Frequency Planning）
2. Ambiguity 分析
3. Synthetic Range 計算
4. 距離精度分析
5. Phase Noise 傳播分析
6. Phase Unwrapping 穩健度分析
7. 最佳頻率組合搜尋
8. 視覺化設計空間探索

供 System Architect 在規劃 iToF 系統時使用。

---

# 數學模型

## 單頻 Unambiguous Range

$$
R = \frac{c}{2f}
$$

其中：

R = 單頻可唯一量測距離範圍

---

### 範例

| 頻率 | Unambiguous Range |
|--------|--------|
| 10 MHz | 15 m |
| 20 MHz | 7.5 m |
| 40 MHz | 3.75 m |
| 80 MHz | 1.875 m |
| 100 MHz | 1.5 m |

---

## 距離精度

假設相位誤差：

$$
\sigma_\phi
$$

則距離誤差：

$$
\sigma_d =
\frac{c}{4\pi f}
\sigma_\phi
$$

結論：

```text
頻率越高
距離解析度越高
```

因此：

高頻負責 Precision。

---

## Synthetic Range

兩個頻率：

$$
f_1
$$

$$
f_2
$$

形成：

$$
R_{syn} =
\frac{c}{2|f_1 - f_2|}
$$

稱為：

- Synthetic Range
- Beat Wavelength Range

---

### 範例

| 頻率組合 | Synthetic Range |
|--------|--------|
| 80 / 70 MHz | 15 m |
| 80 / 75 MHz | 30 m |
| 100 / 90 MHz | 15 m |

頻率差越小：

```text
Synthetic Range 越大
```

---

## Noise Amplification

頻率差越小：

雖然：

```text
Synthetic Range ↑
```

但：

```text
Phase Noise 放大
```

近似：

$$
\sigma_d \propto
\frac{1}{|f_1 - f_2|}
$$

因此：

```text
頻率太接近
容易 Unwrap 錯誤
```

---

# 頻率規劃的六大限制條件

## Constraint 1

最大量測距離

決定：

```text
最低頻率必須多低
```

---

## Constraint 2

距離精度需求

決定：

```text
最高頻率必須多高
```

---

## Constraint 3

Pixel Demodulation 頻寬

受限於：

- Transfer Gate
- RC Delay
- Clock Jitter
- Pixel Structure

一般 CMOS iToF：

```text
10 MHz ~ 150 MHz
```

較常見。

---

## Constraint 4

VCSEL Driver 頻寬

頻率越高：

需要：

```text
更快 rise/fall time
更大驅動頻寬
更高功耗
```

---

## Constraint 5

Motion Artifact

多頻率通常需要：

```text
Subframe #1

Subframe #2

Subframe #3
```

移動目標會導致：

```text
不同頻率量測時
物體位置不同
```

造成 phase 不一致。

---

## Constraint 6

SNR

高頻下：

通常 modulation contrast 下降。

需要評估：

```text
Phase Noise
Amplitude
Confidence
```

---

# 工程設計問題

本工具需要回答：

---

## Case 1

輸入：

```text
最大距離 = 5m

目標精度 = ±5mm

Phase Noise = 0.01rad

最高頻率 = 120MHz
```

輸出：

```text
建議頻率：

20 MHz
60 MHz
100 MHz
```

並解釋原因。

---

## Case 2

輸入：

```text
20 MHz

80 MHz
```

輸出：

```text
單頻距離範圍

Synthetic Range

理論精度

Noise Amplification Factor

Unwrap Robustness
```

---

# 系統功能規劃

## 功能一：頻率計算器

輸入：

```text
Frequency
```

輸出：

```text
Unambiguous Range
```

---

## 功能二：頻率對分析器

輸入：

```text
f1

f2
```

輸出：

```text
Synthetic Range

理論精度

穩健度評估

Noise Amplification
```

---

## 功能三：多頻率分析器

輸入：

```text
f1

f2

f3
```

輸出：

```text
最大唯一距離

距離精度

誤差分析

Unwrap Robustness
```

---

## 功能四：Heatmap

生成：

```text
頻率組合熱圖
```

展示：

```text
Range

Precision

Robustness
```

之間的 Trade-off。

---

## 功能五：最佳頻率搜尋器

輸入：

```text
最大距離

目標精度

Phase Noise

頻率上下限
```

輸出：

```text
最佳雙頻方案

最佳三頻方案

最佳四頻方案
```

並給出評分。

---

# 未來進階方向

## Bayesian Phase Unwrapping

建立：

$$
P(d|\phi_1, \phi_2, \phi_3)
$$

而非傳統硬判斷。

---

## Multipath Simulation

模擬：

```text
直接反射

二次反射

玻璃反射

鏡面反射
```

對距離造成的偏移。

---

## Motion Simulation

模擬：

```text
目標移動

Rolling Shutter

Subframe Delay
```

對量測結果的影響。

---

## AI Assisted Unwrapping

研究：

- LightGBM
- XGBoost
- Neural Network

是否能提升：

```text
低 SNR

Multipath

Motion

Glass
```

情境下的解距離能力。

---

# 預期成果

建立一套可供 iToF System Architect 使用的設計工具，使工程師能回答：

> 在已知最大距離、目標精度、Phase Noise、Pixel 頻寬與 VCSEL Driver 限制的條件下，應如何選擇最佳的多頻率組合，以及其背後的數學與物理依據。
