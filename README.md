# Boater-Poll — Crusader vs MerCruiser

A small Flask + SQLite poll. Boaters pick Crusader or MerCruiser, tick their reasons, and can add a comment and some optional details about themselves. A live results page shows the vote split, the top reasons for each brand, a table of what owners picked, and recent comments.

## Run locally
```
pip install -r requirements.txt
python app.py            # http://localhost:5077
```

## Settings (environment variables)
| Variable | Purpose | Default |
|---|---|---|
| `POLL_ADMIN_KEY` | Key for the CSV export | `change-me` (**change it**) |
| `POLL_DB` | Path to the SQLite file | `poll.db` next to app.py |
| `PORT` | Port to listen on | `5077` |

## Export all votes
`/export.csv?key=YOUR_ADMIN_KEY`

## Deploy publicly
Deploy it to any host that runs Python, such as Render, Railway, Fly.io or a VPS.
Start command: `gunicorn app:app`. Keep `POLL_DB` on a persistent disk, or your votes will be lost on redeploy.

## Notes
- Each browser gets one vote, tracked with a cookie. Voting again from the same browser updates the earlier vote instead of adding a new one. This isn't fraud-proof: someone could clear their cookies and vote again.
- To change the reasons or the optional details, edit the lists at the top of `app.py`.
