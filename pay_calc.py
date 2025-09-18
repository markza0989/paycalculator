#!/usr/bin/env python3
import datetime

# 1. Constants
BASE_RATE      = 26.07
PEN_WEEKDAY    = 1.25   # after 18:00 Mon–Fri
PEN_SAT        = 1.25
PEN_SUN        = 1.50
OT_MULTIPLIER  = 2.0
STD_HOURS      = 38

TAX_BRACKETS = [
    (0,      18200,   0.00, 0),
    (18201,  45000,   0.16, 18200),
    (45001, 135000,   0.30, 45000),
    (135001, 190000,   0.37, 135000),
    (190001, float('inf'), 0.45, 190000),
]

# 2. Helpers to parse times & compute durations
def parse_time(s):
    return datetime.datetime.strptime(s, "%H:%M").time()

def hours_between(start, end):
    dt1 = datetime.datetime.combine(datetime.date.today(), start)
    dt2 = datetime.datetime.combine(datetime.date.today(), end)
    if dt2 <= dt1:
        dt2 += datetime.timedelta(days=1)
    return (dt2 - dt1).total_seconds() / 3600

# 3. Determine the rate multiplier for any (day, time)
def get_multiplier(day_str, t):
    day = day_str.lower()
    if day in ["monday","tuesday","wednesday","thursday","friday"]:
        return PEN_WEEKDAY if t >= datetime.time(18,0) else 1.0
    if day == "saturday":
        return PEN_SAT
    if day == "sunday":
        return PEN_SUN
    raise ValueError(f"Unknown day: {day_str}")

# 4. Process one shift into pay-segments
def segments_for_shift(day, start, end, break_start=None, break_end=None):
    segs = []
    # BEFORE break
    if break_start:
        h = hours_between(start, break_start)
        segs.append((h, get_multiplier(day, start)))
        h2 = hours_between(break_end, end)
        segs.append((h2, get_multiplier(day, break_end)))
    else:
        h = hours_between(start, end)
        segs.append((h, get_multiplier(day, start)))
    return segs

# 5. Compute gross with overtime
def compute_gross(shifts):
    all_segments = []
    total_hours = 0.0

    for day, s, e, bs, be in shifts:
        segs = segments_for_shift(day, s, e, bs, be)
        all_segments.extend(segs)
        total_hours += sum(h for h, _ in segs)

    gross = sum(h * BASE_RATE * m for h, m in all_segments)

    # OVERTIME: last hours at OT_MULTIPLIER
    if total_hours > STD_HOURS:
        ot_hours = total_hours - STD_HOURS
        # adjust from the end backwards
        for h, m in reversed(all_segments):
            if ot_hours <= 0:
                break
            use = min(h, ot_hours)
            # remove old
            gross -= use * BASE_RATE * m
            # add overtime
            gross += use * BASE_RATE * OT_MULTIPLIER
            ot_hours -= use

    return gross, total_hours

# 6. Tax and net pay
def compute_net_weekly(gross):
    annual = gross * 52
    # Income tax
    tax = 0.0
    for lo, hi, rate, base in TAX_BRACKETS:
        if annual > lo:
            taxed = min(annual, hi) - base
            tax += taxed * rate
    # LITO (simplified tiers)
    if annual <= 37000:
        lito = 700
    elif annual < 45000:
        lito = 700 - (annual-37000)*0.05
    elif annual < 66667:
        lito = 325 - (annual-45000)*0.015
    else:
        lito = 0
    tax = max(0, tax - lito)
    # Medicare
    medicare = annual * 0.02

    net_annual = annual - tax - medicare
    return net_annual / 52

# 7. Main input loop
def main():
    shifts = []
    print("Enter shifts. Type 'done' when finished.")
    while True:
        day = input("Day: ")
        if day.lower() == "done":
            break
        start = parse_time(input("  Start (HH:MM): "))
        end   = parse_time(input("  End   (HH:MM): "))
        if input("  Meal break? (y/n): ").lower() == "y":
            bs = parse_time(input("    Break start: "))
            be = parse_time(input("    Break end:   "))
        else:
            bs = be = None
        shifts.append((day, start, end, bs, be))

    gross, hrs = compute_gross(shifts)
    net = compute_net_weekly(gross)

    print(f"\nTotal hours worked: {hrs:.2f}h")
    print(f"Gross pay: A${gross:.2f}")
    print(f"Net pay:   A${net:.2f}")

if __name__ == "__main__":
    main()
