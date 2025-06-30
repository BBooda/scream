import joblib
import numpy as np

# 1) Load transformer + regressor
poly, lr = joblib.load('draco_model.pkl')

# 2) Re-create your swept grid
quant_bits  = np.array([8, 12, 16, 20, 24])
comp_levels = np.array([0,  3,   6,   9])
grid = np.array([[q, c, 19800] for q in quant_bits for c in comp_levels])

# 3) Pre-compute predicted bps for every grid point
Xg      = poly.transform(grid)   # if you used PolynomialFeatures
pred_bps = lr.predict(Xg)        # shape (20,)


def best_settings_for(y_target):
    # find the index whose predicted bits/sec is closest
    idx = np.abs(pred_bps - y_target).argmin()
    print(idx)
    q, c = grid[idx]
    return int(q), int(c)

# Example:
desired_bps = 5e6
q_best, c_best = best_settings_for(desired_bps)
print(f"Use quant_bits={q_best}, comp_level={c_best}")


