"""
Pararius, read from the alert emails it sends you (see alerts.py).
The site itself is never searched by the robot.
"""

import alerts

NAME = "Pararius"


def collect():
    return alerts.collect(NAME)
