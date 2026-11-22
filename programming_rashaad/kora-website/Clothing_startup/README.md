# KORA — clothing startup website

A static site (HTML, CSS and plain JavaScript) with no build step. Open `index.html` in a browser, or host the folder on any static host (Netlify, Vercel, GitHub Pages).

```
python3 -m http.server 8080   # then visit http://localhost:8080
```

## What's on the page

- A preloader, then a hero headline that rises in line by line
- A soft pastel gradient in the background that drifts and follows the cursor
- A custom cursor that changes label on hover ("View", "Feel", "Read")
- A marquee that speeds up and reverses with the scroll direction
- A manifesto paragraph that fills in word by word as you scroll
- A product grid with category filters, colour swatches, quick-add sizes and a quick-view dialog
- A bag drawer with quantities, a free-shipping progress bar, and contents saved in the browser
- A lookbook section where scrolling down moves the cards sideways (on phones, you swipe instead)
- Fabric swatches with a light that follows the cursor
- A list of makers with a floating preview that follows the cursor
- Newsletter signup, and a footer with a giant wordmark

## Making it yours

| What | Where |
| --- | --- |
| Brand name "KORA" | Search and replace in `index.html`. The bag is stored under the key `kora-bag` in `js/main.js` |
| Products, prices, colours, sizes | `js/products.js` |
| Lookbook days | `LOOKS` in `js/products.js` |
| Real product photos | Put images in `assets/` and set `image: "assets/your-photo.jpg"` on a product |
| Gradient colours | `--peach`, `--blush`, `--lilac`, `--mint`, `--butter` at the top of `css/style.css` |
| Fonts | `--serif` and `--sans` in `css/style.css`, plus the Google Fonts link in `index.html` |

The garment drawings are SVG sketches in the style of the technical drawings used in pattern-making (`js/garments.js`). They stand in until you have photography.

## Typography

- **Bodoni Moda**: a high-contrast serif for headlines and the wordmark, in the style of the serif logos used by Westside and other fashion houses.
- **Jost**: a geometric sans in the Futura style, for navigation, labels and body text.

Both are free Google Fonts.
