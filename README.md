# Amsterdam flat tracker

A small personal website that lists flats for rent and for sale in Amsterdam
that match my filters. A robot on GitHub refreshes it every morning at about
07:30 Amsterdam time.

## What is in this folder

| Path | What it is |
| --- | --- |
| `docs/` | The website (`index.html`, `style.css`, `app.js`) and its data file `docs/data/listings.json` |
| `scraper/config.py` | **Every filter rule.** Prices, sizes, bedrooms, the postcode list, room/studio words |
| `scraper/filters.py` | The one strict gate that applies those rules to every listing |
| `scraper/test_filters.py` | Automated tests: example listings that must pass or fail |
| `scraper/run.py` | The daily run: collect, re-check, filter, save |
| `scraper/sources/` | One small file per website that is read |
| `scraper/lets.py` | Reads the rental period (dates and durations) from an ad |
| `scraper/scam.py` | Scam signs, registration check and the tags |
| `scraper/register.py` | Postcode lookup in the city's address register (exact addresses only) |
| `.github/workflows/update.yml` | The timetable that starts the daily run on GitHub |

## One-time setup

1. **GitHub account.** Go to <https://github.com/signup> and create a free account.
2. **GitHub Desktop.** Download it from <https://desktop.github.com>, open it and sign in.
3. **Add this folder.** In GitHub Desktop: *File → Add Local Repository…*, choose
   this folder, *Add Repository*.
4. **First save.** Bottom left, type `First version` in the *Summary* box and
   press **Commit to main**.
5. **Upload.** Press **Publish repository** (top bar). Name it `flat-tracker`,
   **untick "Keep this code private"** (free GitHub Pages needs a public
   repository), press *Publish Repository*.
6. **Switch the website on.** On github.com open the repository, then
   *Settings → Pages*. Under *Build and deployment → Source* choose
   **GitHub Actions**.
7. **First run.** Open the *Actions* tab. If asked, press the green button to
   enable workflows. Click **Update listings** on the left, then
   **Run workflow → Run workflow**. It takes about 10 minutes.
8. **Bookmark it.** The address is `https://YOUR-USERNAME.github.io/flat-tracker/`.

## Run an update by hand

GitHub → your repository → **Actions** → **Update listings** → **Run workflow**
→ **Run workflow**. Reload the website when the run shows a green tick.

## If a run fails

GitHub emails you when a run fails, and the website shows a warning next to
"Last updated" when the data is more than a day old.

1. Open **Actions** and click the run with the red cross, then **Re-run all
   jobs**. Most failures are a website being slow for a moment.
2. If it fails again, click the step with the red cross and copy the last 20
   or so lines of text.
3. Open this folder in Claude and paste those lines: "The daily run failed
   with this message, please fix it."

One website changing its layout does **not** fail the run. That source shows
"✗ Failed" (or "returned no listings") under *Sources on the last run* at the
bottom of the website, and the others carry on. Ask Claude to "fix the
<name> source"; the fix is always inside that one file in `scraper/sources/`.

GitHub pauses timetables in repositories with no activity for 60 days. The
daily save counts as activity, so this only matters after a long stretch of
failures. If it happens, GitHub emails you and one click re-enables it.

## Changing my filters

Open `scraper/config.py`. The limits are at the top:

```python
RENT = {"max_price": 1800, "min_m2": 50, "bedrooms": (1, 2)}
BUY = {"max_price": 500_000, "min_m2": 55, "bedrooms": (1, 2)}
```

Save, then in GitHub Desktop: *Commit to main* and *Push origin*. The next run
uses the new values.

## How listings are judged

Every rule is in `scraper/config.py`, in numbered sections. Every listing,
new or already on the site, must pass the gate in `scraper/filters.py` on
every run. Anything unclear or missing is dropped.

- **Three tabs.** Rent (total up to €1,800), Rent €1,800–2,000 (total from
  €1,801 to €2,000, set by `RENT_STRETCH_MAX_PRICE`), and Buy. A listing is
  in exactly one tab; all other rent rules are the same in both rent tabs.
- **Price, size, bedrooms.** Rent up to €1,800 including separately listed
  service costs, 50 m² or more; buy up to €500,000 k.k., 55 m² or more;
  1 or 2 bedrooms ("2 kamers" = 1 bedroom, "3 kamers" = 2).
- **Area.** Only the postcode whitelist counts. Area names are never used.
  The postcode comes from the ad. If the ad prints a street and house
  number but no postcode, the City of Amsterdam's address register is asked
  for that exact address (switch: `USE_ADDRESS_REGISTER`). No postcode
  means dropped.
- **Whole homes only.** Rooms, studios and anything shared are dropped, and
  so is anything whose type is unclear.
- **Long-term only.** Lets under 6 months are dropped, judged on the dates
  and periods in the ad. Fixed terms of 6 months or more are kept and tagged.
- **Reserved homes** (young people, students, seniors, WoningNet, waiting
  lists, urgency) are dropped.
- **Gone.** Let, sold, under option, under offer or reserved: dropped. Also
  dropped when the ad page has disappeared, or could not be loaded three
  runs in a row.
- **Buying.** No auctions, sitting tenants, co-op shares or priceless
  new-build.
- **Scam signs** drop a listing. It is a filter of obvious signs only, so
  stay alert yourself.
- **Duplicates.** The same home on several sites is shown once, linking to
  the most direct ad (order: `SOURCE_PRIORITY`).
- **Tags** on kept listings: "Fixed term: X months", "Check rental
  period", "Private landlord: view before paying", "Check carefully", and
  "Registration allowed" / "No registration" / "Registration: ask".

## Run the tests

```bash
.venv/bin/python -m unittest discover -s scraper -v
```

The last test reads `docs/data/listings.json` and fails if any listing on
the site breaks a rule.

## Good manners

The robot identifies itself honestly, reads each site's `robots.txt` and
obeys it, waits at least two seconds between pages on the same site, and
visits once a day. A site that refuses is left alone; nothing tries to get
around a block. That is why Funda, Pararius and Huurwoningen.nl are not
covered directly.

## Test on my own Mac (optional)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python scraper/run.py
```

```bash
python3 -m http.server 8000 --directory docs
```

Then open <http://localhost:8000>.
