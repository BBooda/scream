import joblib
import numpy as np

# load
poly, lr = joblib.load('draco_model.pkl')

# your discrete knobs
quant_bits  = np.array([8, 12, 16, 20, 24])
comp_levels = np.array([0,  3,   6,   9])

def best_settings_for(target_bps, n_pts):
    # build a grid of (q, c, n_pts)
    grid = np.array([
        [q, c, n_pts]
        for q in quant_bits
        for c in comp_levels
    ])                     # shape (20, 3)

    # forward-predict bits/sec for each row
    Xg      = poly.transform(grid)
    pred_bps = lr.predict(Xg)

    # pick the index of the closest prediction
    i_best = np.abs(pred_bps - target_bps).argmin()
    q_best, c_best, _ = grid[i_best]
    return int(q_best), int(c_best)

# Example usage in your ROS callback:
#   n_pts = points.shape[0]
n_pts = 19800 
desired_bps = 4000000  # whatever target you have
q, c = best_settings_for(desired_bps, n_pts)

print(f"q: {q}, c: {c}")

