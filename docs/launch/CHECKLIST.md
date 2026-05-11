# Launch Day Checklist

## T-15 minutes

- [ ] `python -c "from hydra_sandbox import execute_python; print('OK')"` works
- [ ] `pip index versions hydra-pysandbox` shows 0.1.0
- [ ] GitHub repo is public (not private)
- [ ] GitHub release v0.1.0 is published
- [ ] README renders correctly on GitHub (check first screen)
- [ ] Open all tabs: HN submit, r/Python, r/LocalLLaMA, r/LangChain, Twitter

## T-0 (Submit order, 5 minutes total)

1. [ ] HN submit
   - URL: `https://news.ycombinator.com/submit`
   - Title: paste from `docs/launch/paste/01_hn_title.txt`
   - URL: paste from `docs/launch/paste/02_hn_url.txt`
   - After submit: add comment from `docs/launch/paste/03_hn_first_comment.txt`
   - **COPY the HN URL** — you'll paste it in Reddit and Twitter

2. [ ] Reddit r/Python
   - URL: `https://www.reddit.com/r/Python/submit`
   - Title: `docs/launch/paste/04_reddit_python_title.txt`
   - Body: `docs/launch/paste/05_reddit_python_body.md`

3. [ ] Reddit r/LocalLLaMA
   - URL: `https://www.reddit.com/r/LocalLLaMA/submit`
   - Title: `docs/launch/paste/06_reddit_localllama_title.txt`
   - Body: `docs/launch/paste/07_reddit_localllama_body.md`

4. [ ] Reddit r/LangChain
   - URL: `https://www.reddit.com/r/LangChain/submit`
   - Title: `docs/launch/paste/08_reddit_langchain_title.txt`
   - Body: `docs/launch/paste/09_reddit_langchain_body.md`

5. [ ] Twitter thread
   - URL: `https://twitter.com/compose/tweet`
   - Content: `docs/launch/paste/10_twitter_thread.txt`
   - Tweet each `---`-separated block as a reply to the previous one

## T+30 minutes (first wave)

- [ ] HN: check submissions page, reply to comments within 5 min
- [ ] Reddit: reply to all comments
- [ ] Twitter: reply to mentions
- [ ] Note: HN replies in first 2 hours are CRITICAL for ranking

## T+1 hour

- [ ] Snapshot metrics in `docs/launch/RESULTS.md`:
  - HN points / rank
  - Reddit upvotes / comments
  - GitHub stars delta
  - PyPI downloads (check pypistats in 24h)

## T+24 hours

- [ ] Reply to all GitHub issues that came in
- [ ] Write "what happened" follow-up blog post
- [ ] Update `RESULTS.md` with final numbers

## Templates
Common replies in `docs/launch/REPLIES.md`
