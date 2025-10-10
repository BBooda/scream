import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

import joblib

# load
df = pd.read_csv('draco_bench_v1.csv')

# features & target
X = df[['quant_bits','comp_level','num_points']]
y = df['bits_per_second']

# polynomial features (if you suspect non-linear)
poly = PolynomialFeatures(degree=2, include_bias=False)
X2   = poly.fit_transform(X)

# train/test split
Xtr, Xte, ytr, yte = train_test_split(X2, y, test_size=0.2, random_state=42)

# fit
lr = LinearRegression().fit(Xtr, ytr)
print("Train R²:", lr.score(Xtr,ytr))
print("Test  R²:", lr.score(Xte,yte))

# save
# poly = your fitted PolynomialFeatures
# lr   = your fitted LinearRegression

# Dump them both into a single file
joblib.dump((poly, lr), 'draco_model_v1.pkl')
