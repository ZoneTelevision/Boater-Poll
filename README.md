# Boater-Poll — Crusader vs MerCruiser

A small Flask + SQLite poll. Boaters pick Crusader or MerCruiser, tick their reasons, and can add a comment and some optional details about themselves. A live results page shows the vote split, the top reasons for each brand, a table of what owners picked, and recent comments.

## Run locally
```
pip install -r requirements.txt
python3 app.py           # prints the address to open (first free port from 8420)
```

## Settings (environment variables)
| Variable | Purpose | Default |
|---|---|---|
| `POLL_ADMIN_KEY` | Key for the CSV export | `change-me` (**change it**) |
| `POLL_DB` | Path to the SQLite file | `poll.db` next to app.py |
| `PORT` | Port to listen on | first free port from `8420` |

## Export all votes
`/export.csv?key=YOUR_ADMIN_KEY`

## Put it on the internet (free, votes are kept)
Two free services: **Neon** stores the votes, and **Render** runs the website.

1. **Neon (database):** sign up at neon.com with GitHub and create a project named `boater-poll`.
   Copy the **connection string**. It starts with `postgresql://`.
2. **Render (website):** sign up at render.com with GitHub. Click **New → Blueprint** and pick this repo.
   Render reads `render.yaml` and asks for two values:
   - `DATABASE_URL`: paste the Neon connection string
   - `POLL_ADMIN_KEY`: any password, used for the CSV export
3. Click **Apply**. In about 2 minutes you get a link like `https://boater-poll.onrender.com` to share.

On the free tier, the site sleeps after 15 minutes with no visitors. The next visitor waits about a minute while it wakes up. Votes are never lost, because they're stored in Neon.
Without `DATABASE_URL`, the app uses a local `poll.db` file, which is how it runs on your own computer.

## Notes
- Each browser gets one vote, tracked with a cookie. Voting again from the same browser updates the earlier vote instead of adding a new one. This isn't fraud-proof: someone could clear their cookies and vote again.
- To change the reasons or the optional details, edit the lists at the top of `app.py`.
