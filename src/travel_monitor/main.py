"""Travel Price Monitor - Main entry point."""

import argparse
import json
import logging
import sys
import time

from travel_monitor.notify.telegram_api import TelegramSender
from travel_monitor.price_history import PriceHistory
from travel_monitor.scraper import TravelScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)



def _show_category_table(category_url: str, sort_by: str = "date") -> None:
    """Scrape category page and show trips as table.

    Uses pricing API for ALL departures (not just rendered HTML).
    """
    import re, time, json
    from datetime import date, datetime
    from collections import defaultdict
    from travel_monitor.scraper import TravelScraper

    today = date.today()

    with TravelScraper(headless=True, timeout_ms=90000) as s:
        page = s._browser.new_page()
        page.goto(category_url, wait_until="domcontentloaded")
        time.sleep(10)

        groups_raw = page.evaluate(
            '() => JSON.stringify(window.__NEXT_DATA__.props.'
            'initialState.general.promotionGroups)'
        )
        groups = json.loads(groups_raw)

        if not groups:
            print("No promotion groups found")
            return

        dest = category_url.rstrip("/").split("/")[-1].title()
        all_rows = []
        seen_dep_keys = set()

        for group in groups:
            group_name = group.get("GroupName", "")
            promos = group.get("Promotions", [])

            # Collect unique itinerary IDs from PromoLinks in this group
            itin_ids = set()
            for p in promos:
                link = p.get("PromoLink", "")
                m = re.search(r"itinerary=(\d+)", link)
                if m:
                    itin_ids.add(int(m.group(1)))

            # Call pricing API for each itinerary
            for it_id in itin_ids:
                try:
                    resp = page.evaluate(
                        f'''async () => {{
                            const r = await fetch(
                                "/api/organized/pricing/?itinerary={it_id}&isStaticPage=true&capacity=2_0_0&clientClubType=0&referrer="
                            );
                            return await r.text();
                        }}'''
                    )
                    api_data = json.loads(resp)
                except Exception:
                    continue

                departures = api_data.get("itineraryDepartures", {})

                # Get itinerary name from API itineraries
                itin_obj = api_data.get("itineraries", {}).get(str(it_id), {})
                itinerary_name = ""
                if isinstance(itin_obj, dict):
                    # Could be {Id, ItineraryId, ...} or {Name, ...}
                    for k in ("Name", "NameEn", "Title"):
                        val = itin_obj.get(k)
                        if val:
                            itinerary_name = val
                            break

                if not itinerary_name:
                    # Fallback: use first promo title for this itinerary
                    for p in promos:
                        link = p.get("PromoLink", "")
                        if f"itinerary={it_id}" in link:
                            itinerary_name = p.get("Title", "")
                            break

                for dep_key, dep_data in departures.items():
                    if dep_key in seen_dep_keys:
                        continue
                    seen_dep_keys.add(dep_key)

                    sd = dep_data.get("StartDate", "")
                    ed = dep_data.get("EndDate", "")

                    # Skip past
                    try:
                        sd_date = datetime.strptime(sd, "%d.%m.%Y").date()
                    except (ValueError, TypeError):
                        sd_date = None
                    if sd_date and sd_date <= today:
                        continue

                    # Calculate days
                    try:
                        ed_date = datetime.strptime(ed, "%d.%m.%Y").date()
                        days_count = (ed_date - sd_date).days + 1 if sd_date else 0
                    except (ValueError, TypeError):
                        days_count = 0

                    # Guide
                    guide = dep_data.get("GuideName") or "\u2014"
                    guide_display = guide[:18] if guide != "\u2014" else guide

                    # Seats
                    seats = dep_data.get("SeatsLeft")
                    seats_str = str(seats) if seats is not None else ""

                    # Price
                    rp_dict = dep_data.get("RoomPricesDictionary", {})
                    price_num = float("inf")
                    price_str = "?"
                    if "2_0_0" in rp_dict:
                        room_info = rp_dict["2_0_0"]
                        rp = room_info.get("RoomPrice", {})
                        pval = rp.get("DisplayPriceAfterDiscount") or rp.get("PriceAfterDiscount", 0)
                        if pval:
                            total_pax = room_info.get("TotalPax", 2)
                            per_person = pval // total_pax
                            price_num = float(per_person)
                            price_str = f"\u20AC{per_person:,}"

                    # Format dates
                    def fmt_heb(d: str) -> str:
                        try:
                            dt = datetime.strptime(d, "%d.%m.%Y")
                            return dt.strftime("%d/%m")
                        except (ValueError, TypeError):
                            return d or "?"

                    date_str = f"{fmt_heb(sd)} - {fmt_heb(ed)}"

                    # Flight times
                    dep_time = dep_data.get("StartTime", "")
                    ret_time = dep_data.get("EndTime", "")

                    all_rows.append({
                        "date_sort": sd_date or date.max,
                        "price_sort": price_num,
                        "days_sort": days_count,
                        "group": group_name,
                        "trip_name": itinerary_name,
                        "it_id": it_id,
                        "dates": date_str,
                        "depart": dep_time,
                        "return": ret_time,
                        "days": str(days_count),
                        "price": price_str,
                        "guide": guide_display,
                        "seats": seats_str,
                    })



        page.close()

    if not all_rows:
        print("No upcoming trips found")
        return

    sort_cols = {
        "date": lambda r: (r["date_sort"], r["price_sort"]),
        "price": lambda r: (r["price_sort"], r["date_sort"]),
        "duration": lambda r: (r["days_sort"], r["price_sort"]),
    }
    all_rows.sort(key=sort_cols.get(sort_by, sort_cols["date"]))

    # Snapshot tracking - detect any field changes
    ph = PriceHistory()
    for r in all_rows:
        key = f"{r['it_id']}|{r['dates']}"
        result = ph.update(key, r)
        r["change"] = result["change_label"]

    # Hide sold-out trips from display (still tracked for change detection)
    all_rows = [r for r in all_rows if r["seats"].strip() != "0"]

    if not all_rows:
        print("No available trips found")
        return

    # Group by (group_name, trip_name) tuple
    grouped = defaultdict(list)
    for r in all_rows:
        grouped[(r["group"], r["trip_name"])].append(r)

    LRE = "\u202a"
    PDF = "\u202c"
    H = {"dates": "Dates", "depart": "Departure", "ret": "Return", "days": "Days", "price": "Price", "seats": "Seats", "change": "Change"}
    sep = "-" * 110
    hdr_cols = LRE + f"{H['dates']:<22} | {H['depart']:<11} | {H['ret']:<11} | {H['days']:<5} | {H['price']:<10} | {H['seats']:<14} | {H['change']:<10}" + PDF
    dash_line = LRE + sep + PDF

    out_lines = [f"\n--- {dest} Trips ---"]
    for (gname, tname), trips in grouped.items():
        h = f"{gname} \u2014 {tname}" if tname else gname
        out_lines.append(f"\n{h}")
        out_lines.append("-" * 100)
        out_lines.append(hdr_cols)
        out_lines.append(dash_line)
        for t in trips:
            out_lines.append(
                LRE + f"{t['dates']:<22} | {t['depart']:<11} | {t['return']:<11} | {t['days']:<5} | {t['price']:<10} | {('Sold out' if t['seats'].strip() == '0' else t['seats']):<14} | {t.get('change', ''):<10}" + PDF
            )
        out_lines.append("-" * 100)

    out = "\n".join(out_lines)
    print(out)

    _try_send_telegram(all_rows, grouped, dest)

def _try_send_telegram(all_rows: list, grouped: dict, dest: str):
    tg = TelegramSender()
    if not tg.configured:
        return
    has_changes = any(r.get("change") for r in all_rows)
    if not has_changes:
        logger.info("No changes detected, skipping Telegram notification")
        return
    tg_parts = []
    for (gname, tname), trips in grouped.items():
        h = f"{gname} \u2014 {tname}" if tname else gname
        tg_parts.append(f"<b>{h}</b>")
        trip_lines = []
        for t in trips:
            seats = "\U0001f6ab" if t["seats"].strip() == "0" else f"\U0001f4ba{t['seats']}"
            ch = t.get("change", "")
            if ch:
                ch = ch.replace("\u2193", "\u2b07\ufe0f").replace("\u2191", "\u2b06\ufe0f")
                ch = f"  {ch}"
            trip_lines.append(
                f"\U0001f4c5 {t['dates']}  \U0001f5d3\ufe0f{t['days']}  \U0001f6eb{t['depart']} \U0001f6ec{t['return']}"
                f"\n\U0001f4b0{t['price']}  {seats}{ch}"
            )
        tg_parts.append("\n\n".join(trip_lines))
    tg.send_text("\n\n".join(tg_parts))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Travel Price Monitor")
    parser.add_argument("--dest", help="Destination slug (e.g. macedonia, montenegro)")
    parser.add_argument("--sort", choices=["date", "price", "duration"], default="date", help="Category table sort order")
    parser.add_argument("--period", type=int, metavar="MINUTES", help="Run repeatedly every N minutes")
    parser.add_argument("--albania", action="store_true", help="Show Albania trips")
    parser.add_argument("--romania", action="store_true", help="Show Romania trips")
    parser.add_argument("--macedonia", action="store_true", help="Show North Macedonia trips")
    
    args = parser.parse_args()

    def _pick_url() -> str | None:
        if args.albania:
            return "https://www.eshet.com/organized/europe/albania/"
        if args.romania:
            return "https://www.eshet.com/organized/europe/romania/"
        if args.macedonia:
            return "https://www.eshet.com/organized/europe/macedonia/"
        if args.dest:
            return f"https://www.eshet.com/organized/europe/{args.dest}/"
        return None

    url = _pick_url()
    if url:
        interval = (args.period or 0) * 60
        while True:
            try:
                _show_category_table(url, sort_by=args.sort)
            except Exception as e:
                logger.error(f"Scrape failed: {e}")
                if not interval:
                    raise
            if not interval:
                break
            for remaining in range(interval, 0, -1):
                mins, secs = divmod(remaining, 60)
                print(f"\rNext check in {mins:02d}:{secs:02d}  ", end="", flush=True)
                time.sleep(1)
            print()
        return


    parser.print_help()


if __name__ == "__main__":
    main()