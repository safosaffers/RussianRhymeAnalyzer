import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from scipy.sparse.linalg import eigsh
from scipy.sparse import csr_matrix
import warnings
warnings.filterwarnings('ignore')

# Фонетическая векторизация слогов вынесена в общий модуль (см. Model/Phonetics.py):
# схожесть слогов = косинус векторов фонетических признаков (гласная + согласные),
# вместо прежней «энергии» по порядку буквы в алфавите.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from Model.Phonetics import syllable_energy, syllable_similarity

# ============================================================
# 1. ИСХОДНАЯ СТРУКТУРА: Расслоенное пространство над решеткой
# ============================================================

# Входной текст (стихотворение)
text = """
Буря мглою небо кроет
Вихри снежные крутя
То как зверь она завоет
То заплачет как дитя
"""

# Алфавит и классификация
vowels = set('аеёиоуыэюя')
consonants = set('бвгджзйклмнпрстфхцчшщъь')

def split_into_syllables(word):
    """
    Простейший слогораздел: каждый слог содержит ровно одну гласную.
    Согласные присоединяются к следующей гласной (кроме начала слова).
    Возвращает список слогов.
    """
    word = word.lower()
    syllables = []
    current = ""
    for char in word:
        if char in consonants:
            current += char
        elif char in vowels:
            current += char
            syllables.append(current)
            current = ""
        else:
            if current:
                current += char
    if current:
        # Если остались согласные без гласной, присоединяем к последнему слогу
        if syllables:
            syllables[-1] += current
        else:
            syllables.append(current)
    return syllables

# Разбор текста: создаём решетку (строка = строка стиха, столбец = позиция слога в строке)
lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
syllable_grid = []  # syllable_grid[i][j] = слог или None
max_cols = 0
for line in lines:
    words = line.split()
    line_syllables = []
    for word in words:
        line_syllables.extend(split_into_syllables(word))
    syllable_grid.append(line_syllables)
    max_cols = max(max_cols, len(line_syllables))

# Выравниваем до прямоугольной матрицы (разреженная: пустоты = None)
for i in range(len(syllable_grid)):
    while len(syllable_grid[i]) < max_cols:
        syllable_grid[i].append(None)

print("Слоговая решётка (расслоенное пространство):")
for i, row in enumerate(syllable_grid):
    print(f"Строка {i}: {row}")

# ============================================================
# 2. КОЛЛАПС СЛОЯ (РЕНОРМАЛИЗАЦИЯ): слог -> число
# ============================================================

# Формируем матрицу энергий E(i, j)
n_rows = len(syllable_grid)
n_cols = max_cols
E = np.full((n_rows, n_cols), np.nan)
syllable_map = {}  # словарь: (i,j) -> слог (только для непустых)
flat_nodes = []     # список координат непустых узлов

for i in range(n_rows):
    for j in range(n_cols):
        s = syllable_grid[i][j]
        if s is not None:
            E[i, j] = syllable_energy(s)
            syllable_map[(i, j)] = s
            flat_nodes.append((i, j))

print("\nМатрица энергий E(i,j):")
print(E)
# ============================================================
# 3. МАТЕМАТИКА СВЯЗЕЙ (ЭКРАНИРОВАНИЕ): потенциал Юкавы
# ============================================================

def manhattan_distance(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def yukawa_kernel(d, lam=0.8):
    """Экранированное взаимодействие: подавляет дальние связи."""
    if d == 0:
        return 1.0  # самосвязь
    return np.exp(-lam * d) / d

N = len(flat_nodes)
node_index = {pos: idx for idx, pos in enumerate(flat_nodes)}

# Строим матрицу связей S_ij (только для непустых узлов)
S = np.zeros((N, N))

for a in range(N):
    for b in range(a + 1, N):
        pos_a = flat_nodes[a]
        pos_b = flat_nodes[b]
        d = manhattan_distance(pos_a, pos_b)
        sim = syllable_similarity(syllable_map[pos_a], syllable_map[pos_b])
        # Произведение энергий как дополнительный фактор силы
        energy_factor = abs(E[pos_a] * E[pos_b]) / 10.0  # нормируем
        S[a, b] = sim * yukawa_kernel(d) * energy_factor
        S[b, a] = S[a, b]

# Самосвязи
for a in range(N):
    S[a, a] = 1.0

print("\nФрагмент матрицы связей S (первые 5x5):")
print(S[:5, :5])

# ============================================================
# 4. ЭФФЕКТ РЕЗОНАНСА: тройные корреляции (ритм)
# ============================================================

def apply_resonance(S, gamma=0.3):
    """
    Усиливаем связи, если у пары узлов есть общие «друзья» — тройная корреляция.
    S_final[a,b] = S[a,b] + gamma * sum_c (S[a,c] * S[b,c]) / N
    """
    S_new = S.copy()
    N = S.shape[0]
    for a in range(N):
        for b in range(a + 1, N):
            # Суммируем влияние общих соседей
            resonance = 0.0
            for c in range(N):
                if c != a and c != b:
                    resonance += S[a, c] * S[b, c]
            resonance /= N
            S_new[a, b] += gamma * resonance
            S_new[b, a] = S_new[a, b]
    return S_new

S_resonant = apply_resonance(S, gamma=0.3)

print("\nМатрица связей после резонанса (первые 5x5):")
print(S_resonant[:5, :5])

# Нормируем S в диапазон [0, 1] для стабильности
S_norm = S_resonant / np.max(S_resonant)
# ============================================================
# 5. ВЫХОД АЛГОРИТМА: спектральное вложение и цвет
# ============================================================

def spectral_embedding(S, n_components=3):
    """
    Спектральное вложение через Лапласиан.
    Слабые связи автоматически «гаснут» — узлы с малыми значениями
    в S стягиваются к началу координат (чёрный цвет).
    """
    # Степени вершин
    degrees = np.sum(S, axis=1)
    D_inv_sqrt = np.diag(1.0 / np.sqrt(degrees + 1e-10))

    # Нормализованный Лапласиан: L = I - D^{-1/2} S D^{-1/2}
    L = np.eye(N) - D_inv_sqrt @ S @ D_inv_sqrt

    # Собственные векторы (пропускаем нулевой)
    eigenvalues, eigenvectors = np.linalg.eigh(L)

    # Берём n_components наименьших ненулевых собственных векторов
    embedding = eigenvectors[:, 1:n_components+1]

    # Нормируем для RGB
    for k in range(n_components):
        col = embedding[:, k]
        min_val, max_val = np.min(col), np.max(col)
        if max_val - min_val > 1e-10:
            embedding[:, k] = (col - min_val) / (max_val - min_val)
        else:
            embedding[:, k] = 0.5

    return embedding

embedding = spectral_embedding(S_norm, n_components=3)

# Создаём RGB-цвета для каждого узла
colors_rgb = embedding.copy()

# Если у узла очень слабые связи (изоляция), его цвет гасится
isolation_mask = np.sum(S_norm, axis=1) < 0.1
colors_rgb[isolation_mask] = [0, 0, 0]  # чёрный

print("\nЦвета (RGB) для каждого слога:")
for idx, pos in enumerate(flat_nodes):
    syllable = syllable_map[pos]
    rgb = colors_rgb[idx]
    print(f"  [{pos}] '{syllable}' -> RGB({rgb[0]:.2f}, {rgb[1]:.2f}, {rgb[2]:.2f})")

# ============================================================
# ВИЗУАЛИЗАЦИЯ
# ============================================================

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# --- Подграфик 1: Матрица энергий E ---
ax1 = axes[0]
mask = ~np.isnan(E)
E_masked = np.ma.array(E, mask=~mask)
im1 = ax1.imshow(E_masked, cmap='viridis', aspect='auto')
ax1.set_title('Матрица энергий E(i,j)')
for i in range(n_rows):
    for j in range(n_cols):
        if mask[i, j]:
            ax1.text(j, i, syllable_grid[i][j], ha='center', va='center',
                     fontsize=8, color='white' if E[i,j] > 5 else 'black')
ax1.set_xlabel('Позиция в строке')
ax1.set_ylabel('Строка')
plt.colorbar(im1, ax=ax1, label='Энергия')

# --- Подграфик 2: Матрица связей S ---
ax2 = axes[1]
im2 = ax2.imshow(S_norm, cmap='hot', aspect='auto')
ax2.set_title('Матрица рифм (нормированная)')
ax2.set_xlabel('Индекс слога')
ax2.set_ylabel('Индекс слога')
plt.colorbar(im2, ax=ax2, label='Сила связи')

# --- Подграфик 3: Цветовая карта стихотворения ---
ax3 = axes[2]
color_grid = np.zeros((n_rows, n_cols, 3))
for idx, pos in enumerate(flat_nodes):
    color_grid[pos[0], pos[1]] = colors_rgb[idx]

# Пустые ячейки — белые
for i in range(n_rows):
    for j in range(n_cols):
        if np.all(color_grid[i, j] == 0) and syllable_grid[i][j] is None:
            color_grid[i, j] = [1, 1, 1]  # белый для пустых

ax3.imshow(color_grid, aspect='auto')
ax3.set_title('Цветовая карта стихотворения')
for i in range(n_rows):
    for j in range(n_cols):
        if syllable_grid[i][j] is not None:
            rgb = color_grid[i, j]
            # Выбираем контрастный цвет текста
            luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            text_color = 'white' if luminance < 0.5 else 'black'
            ax3.text(j, i, syllable_grid[i][j], ha='center', va='center',
                     fontsize=8, color=text_color, fontweight='bold')
ax3.set_xlabel('Позиция в строке')
ax3.set_ylabel('Строка')

plt.tight_layout()
plt.savefig('poem_analysis.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nГотово! Картинка сохранена как poem_analysis.png")
print("\nИнтерпретация:")
print("- Похожие цвета = рифмующиеся слоги (с учётом затухания на расстоянии)")
print("- Чёрные или очень тёмные = изолированные/слабые связи («погасли»)")
print("- Яркие близкие цвета = резонансные цепочки (ритмический рисунок)")
