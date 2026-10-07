"""Synthetic ATMACA flight logs with known ground truth.

Produces flights in the *normalized sample format* used by the ground station's metric engine
(one CSV per flight) plus a truth JSON with the values the metrics must reproduce.

Why normalized and not raw blackbox_decode CSV?  The exact column names of INAV's decoder output
must be taken from a real decoded log (bench log as soon as the flight controller arrives).
The ground station therefore has two layers:  parser (decoder CSV -> normalized samples) and
metric engine (normalized samples -> metrics).  These files test the second layer today.

Usage:  python synthlog.py out_dir
"""
import csv
import json
import math
import os
import random
import sys

HZ = 10                     # samples per second in the normalized format
DT = 1.0 / HZ
HOME_LAT, HOME_LON = 41.17000, 29.60000
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(HOME_LAT))
CAPACITY = 3000.0

COLUMNS = ["time_s", "armed", "lat", "lon", "alt_m", "ground_speed_ms", "vbat_v", "current_a", "mah_drawn",
           "flight_mode", "rth_reason", "failsafe", "rc_link_ok", "sticks_centered", "gps_sats"]


class Sim:
    def __init__(self, seed):
        self.rnd = random.Random(seed)
        self.t = 0.0
        self.x = self.y = self.z = 0.0          # metres east / north / up from home
        self.mah = 0.0
        self.rows = []
        self.armed = 1

    def latlon(self, x, y):
        return HOME_LAT + y / M_PER_DEG_LAT, HOME_LON + x / M_PER_DEG_LON

    def step(self, vx, vy, vz, mode, current, reason="", failsafe=0, link=1, centered=0, noise=0.0):
        px, py = self.x, self.y
        self.x += vx * DT
        self.y += vy * DT
        self.z = max(0.0, self.z + vz * DT)
        self.mah += current * DT / 3.6           # A * s -> mAh
        self.t += DT
        nx = self.x + self.rnd.gauss(0, noise)
        ny = self.y + self.rnd.gauss(0, noise)
        lat, lon = self.latlon(nx, ny)
        speed = math.hypot(self.x - px, self.y - py) / DT
        cells = 6
        vcell = 4.15 - 0.55 * (self.mah / CAPACITY) - 0.012 * current
        self.rows.append({
            "time_s": round(self.t, 2), "armed": self.armed, "lat": f"{lat:.7f}", "lon": f"{lon:.7f}",
            "alt_m": round(self.z, 2), "ground_speed_ms": round(speed, 2), "vbat_v": round(vcell * cells, 2),
            "current_a": round(current, 2), "mah_drawn": round(self.mah, 1), "flight_mode": mode,
            "rth_reason": reason, "failsafe": failsafe, "rc_link_ok": link, "sticks_centered": centered,
            "gps_sats": 14,
        })

    def dist(self):
        return math.hypot(self.x, self.y)

    # ---- manoeuvres
    def climb(self, alt, mode="EASY", rate=2.0, current=14.0):
        while self.z < alt - 1e-6:
            self.step(0, 0, min(rate, (alt - self.z) / DT), mode, current)

    def fly_to(self, tx, ty, speed, mode, current=16.0, reason="", failsafe=0, link=1, stop_if=None):
        while True:
            dx, dy = tx - self.x, ty - self.y
            d = math.hypot(dx, dy)
            if d < speed * DT:
                self.step(dx / DT, dy / DT, 0, mode, current, reason, failsafe, link)
                return
            self.step(dx / d * speed, dy / d * speed, 0, mode, current, reason, failsafe, link)
            if stop_if and stop_if(self):
                return

    def hover(self, seconds, mode="EASY", current=12.0, offsets=None):
        """offsets: callable(t) -> (dx, dy, dz) applied around the hold point (exact, no extra noise)."""
        hx, hy, hz = self.x, self.y, self.z
        n = int(round(seconds * HZ))
        for i in range(n):
            ox, oy, oz = offsets(i * DT) if offsets else (0.0, 0.0, 0.0)
            self.x, self.y = hx + ox, hy + oy
            self.z = hz + oz
            self.step(0, 0, 0, mode, current, centered=1)
            self.x, self.y, self.z = hx + ox, hy + oy, hz + oz

    def descend(self, mode, reason="", rate_hi=2.0, rate_lo=1.0, slow_alt=10.0, current=11.0):
        while self.z > 0.0:
            rate = rate_hi if self.z > slow_alt else rate_lo
            self.step(0, 0, -min(rate, self.z / DT), mode, current, reason, centered=1)
        for _ in range(int(1.0 * HZ)):            # landing detector delay, then disarm
            self.step(0, 0, 0, mode, 4.0, reason, centered=1)
        self.armed = 0
        self.step(0, 0, 0, mode, 0.5, reason, centered=1)

    def write(self, path):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(self.rows)


def drift_offsets(target_rms, seconds, seed):
    """Smooth horizontal wander that starts at 0 (hold point) with a known RMS distance."""
    rnd = random.Random(seed)
    comps = [(rnd.uniform(0.02, 0.12), rnd.uniform(0, 2 * math.pi), rnd.uniform(0.5, 1.0)) for _ in range(6)]

    def raw(t):
        x = sum(a * (math.sin(2 * math.pi * f * t + p) - math.sin(p)) for f, p, a in comps[:3])
        y = sum(a * (math.sin(2 * math.pi * f * t + p) - math.sin(p)) for f, p, a in comps[3:])
        return x, y
    n = int(seconds * HZ)
    vals = [raw(i * DT) for i in range(n)]
    rms = math.sqrt(sum(x * x + y * y for x, y in vals[2 * HZ:]) / len(vals[2 * HZ:]))
    k = target_rms / rms
    return lambda t: (raw(t)[0] * k, raw(t)[1] * k, 0.25 * math.sin(2 * math.pi * 0.07 * t))


# ---------------------------------------------------------------- scenarios
def hover_test(out, name, target_rms, seed):
    s = Sim(seed)
    s.climb(8)
    s.fly_to(20, 25, 4, "EASY")
    for _ in range(int(3 * HZ)):                  # braking: pilot still has sticks deflected
        s.step(0, 0, 0, "EASY", 12.0, centered=0)
    hold_start = s.t
    off = drift_offsets(target_rms, 61, seed + 1)
    s.hover(61, offsets=off)
    hold_end = s.t
    s.fly_to(-30, 10, 5, "NORMAL", 18)
    s.fly_to(0, 0, 5, "NORMAL", 18)
    s.descend("LAND")
    s.write(os.path.join(out, f"{name}.csv"))
    # truth: RMS / max of injected offsets after the 2 s settling window
    vals = [off(i * DT) for i in range(int(61 * HZ))][2 * HZ:]
    d = [math.hypot(x, y) for x, y, _ in vals]
    alt = [z for _, _, z in vals]          # relative to the hold altitude (offset 0 at t = 0)
    truth = {"scenario": "hover", "hover_segment_s": [round(hold_start, 1), round(hold_end, 1)],
             "hover_drift_rms_m": round(math.sqrt(sum(v * v for v in d) / len(d)), 2),
             "hover_drift_max_m": round(max(d), 2),
             "alt_hold_rms_m": round(math.sqrt(sum(v * v for v in alt) / len(alt)), 2)}
    json.dump(truth, open(os.path.join(out, f"{name}.truth.json"), "w"), indent=2)


def guest_fence(out, seed=7, R=50.0, H=30.0, m=15.0, confirm=1.0, response=0.7):
    s = Sim(seed)
    s.climb(8)
    s.fly_to(10, 10, 3, "EASY")
    ang = math.radians(40)
    breach_t = None
    # fly outwards until the breach is confirmed and the response delay has passed
    while True:
        s.step(4 * math.cos(ang), 4 * math.sin(ang), 0, "EASY", 15)
        if breach_t is None and s.dist() > R:
            breach_t = s.t
        if breach_t is not None and s.t >= breach_t + confirm + response - 1e-9:
            break
    rth_t = s.t
    # momentum: decelerate 4 -> 0 m/s in 2 s while turning back
    v = 4.0
    while v > 0:
        v = max(0.0, v - 2.0 * DT)
        s.step(v * math.cos(ang), v * math.sin(ang), 0, "RTH", 15, reason="FENCE")
    max_d = s.dist()
    while s.dist() > R - m:
        d = s.dist()
        s.step(-s.x / d * 4, -s.y / d * 4, 0, "RTH", 15, reason="FENCE")
    release_t = s.t
    for _ in range(int(2 * HZ)):
        s.step(0, 0, 0, "EASY", 12, centered=1)
    s.fly_to(5, -12, 3, "EASY")
    s.descend("LAND")
    s.write(os.path.join(out, "guest_fence.csv"))
    truth = {"scenario": "fence", "R_m": R, "H_m": H, "release_margin_m": m, "confirm_s": confirm,
             "breach_first_exceed_s": round(breach_t, 1), "rth_start_s": round(rth_t, 1),
             "fence_response_s": round(rth_t - (breach_t + confirm), 2),
             "fence_overshoot_h_m": round(max_d - R, 2), "fence_overshoot_v_m": 0.0,
             "release_s": round(release_t, 1)}
    json.dump(truth, open(os.path.join(out, "guest_fence.truth.json"), "w"), indent=2)


def battery_rth(out, seed=11, k=0.9, r=0.20, L=150.0, confirm=2.0, warn=5.0):
    s = Sim(seed)
    s.climb(20, "NORMAL", current=18)
    usable = CAPACITY * (1 - r)
    T = lambda d: usable - L - k * d
    # loiter far away until the threshold is crossed and confirmed, then warning period
    cross_t, trigger = None, None
    s.fly_to(260, 190, 9, "NORMAL", 22)                       # ~322 m out
    while True:
        s.step(0.4 * math.sin(s.t / 7), 0.4 * math.cos(s.t / 7), 0, "NORMAL", 24)
        over = s.mah >= T(s.dist())
        if over and cross_t is None:
            cross_t = s.t
        if not over:
            cross_t = None
        if cross_t is not None and s.t >= cross_t + confirm - 1e-9 and trigger is None:
            trigger = (s.t, s.mah, T(s.dist()), s.dist())
        if trigger and s.t >= trigger[0] + warn - 1e-9:
            break
    rth_t, rth_mah, rth_d = s.t, s.mah, s.dist()
    s.climb(30, "RTH", current=20)
    for row in s.rows:
        if row["time_s"] > rth_t:
            row["rth_reason"] = "BATTERY"
    climb_end_mah, climb_end_d = s.mah, s.dist()
    # straight home (trackback omitted for simplicity) with return cost ~= k mAh per metre
    speed = 9.0
    cur = k * speed * 3.6                                    # A such that mAh per metre == k
    hx, hy = 1.6, -1.2                                       # lands 2.0 m from the take-off point
    s.fly_to(hx, hy, speed, "RTH", cur, reason="BATTERY")
    for row in s.rows[-int(rth_d / speed * HZ) - 2:]:
        row["rth_reason"] = "BATTERY"
    descent_mah = s.mah
    s.descend("RTH", reason="BATTERY", current=11)
    s.write(os.path.join(out, "battery_rth.csv"))
    truth = {"scenario": "battery", "C_mAh": CAPACITY, "r": r, "L_mAh": L, "k_mAh_per_m": k,
             "confirm_s": confirm, "warning_s": warn,
             "trigger_s": round(trigger[0], 1), "trigger_mah": round(trigger[1], 1),
             "threshold_at_trigger_mah": round(trigger[2], 1),
             "battery_threshold_error_mah": round(trigger[1] - trigger[2], 1),
             "rth_start_s": round(rth_t, 1), "rth_start_distance_m": round(rth_d, 1),
             "landing_error_m": round(math.hypot(hx, hy), 2),
             "remaining_mah": round(CAPACITY - s.mah, 0),
             "k_estimate_mAh_per_m": round((descent_mah - climb_end_mah) / climb_end_d, 3)}
    json.dump(truth, open(os.path.join(out, "battery_rth.truth.json"), "w"), indent=2)


def failsafe_rth(out, seed=21, guard=0.5):
    s = Sim(seed)
    s.climb(18, "NORMAL", current=18)
    s.fly_to(200, 165, 10, "NORMAL", 22)                    # ~259 m
    lost_t = s.t
    for _ in range(int(guard * HZ)):
        s.step(0, 0, 0, "NORMAL", 14, link=0)
    rth_t = s.t
    s.climb(30, "RTH", current=20)
    s.rows[-1]["rth_reason"] = "FAILSAFE"
    for row in s.rows:
        if row["time_s"] > rth_t:
            row.update(failsafe=1, rc_link_ok=0, rth_reason="FAILSAFE")
    restored = lambda sim: sim.dist() < 120
    s.fly_to(0, 0, 9, "RTH", 19, reason="FAILSAFE", failsafe=1, link=0, stop_if=restored)
    restored_t = s.t
    for _ in range(int(0.8 * HZ)):                          # link back, pilot moves sticks
        s.step(-3, -2.4, 0, "RTH", 18, reason="FAILSAFE", failsafe=1, link=1)
    regain_t = s.t
    s.fly_to(0.8, 0.6, 6, "NORMAL", 18)
    s.descend("NORMAL")
    s.write(os.path.join(out, "failsafe_rth.csv"))
    truth = {"scenario": "failsafe", "link_lost_s": round(lost_t, 1), "rth_start_s": round(rth_t, 1),
             "failsafe_response_s": round(rth_t - lost_t, 2), "link_restored_s": round(restored_t, 1),
             "control_regained_s": round(regain_t, 1)}
    json.dump(truth, open(os.path.join(out, "failsafe_rth.truth.json"), "w"), indent=2)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "samples"
    os.makedirs(out, exist_ok=True)
    hover_test(out, "hover_before_tuning", 1.9, seed=3)
    hover_test(out, "hover_after_tuning", 1.2, seed=5)
    guest_fence(out)
    battery_rth(out)
    failsafe_rth(out)
    print("written to", out)
