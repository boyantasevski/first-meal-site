# First Meal site

The support page, the privacy policy, the shared shopping list page and the recipe pages for the First Meal iOS app. Deployed to GitHub Pages by the workflow on every push to `main`.

- `index.html`, `privacy.html`: support and privacy.
- `list.html`: a shopping list shared from the app; the list travels in the link's fragment and the ticks stay in the browser. Nothing is sent anywhere.
- `recipe/<id>.html`: one page per recipe, for the app's Share button. Generated, `noindex`, not linked from the site.
- `tools/build.py`: builds the recipe pages, the dish cut-outs (`img/dishes/`) and the 1200 × 630 share images (`img/og/`, including `list.jpg` for the shopping list) from `data/plan-and-recipes.json`, a copy of the app's content file. Re-run it when the content or the photos change: `python3 tools/build.py --photos "<folder with <id>-spoon.png / <id>-finger.png>"`.
