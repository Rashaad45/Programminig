/*
 * Edit your catalogue here.
 *  - category: "women" | "men" | "unisex"
 *  - garment:  "tee" | "overshirt" | "trouser" | "dress" | "kurta" | "jacket"
 *  - image:    optional path to a real photo (e.g. "assets/overshirt.jpg")
 */
window.PRODUCTS = [
  {
    id: 'everyday-tee',
    name: 'Everyday Tee',
    fig: 'Fig. 01',
    price: 1490,
    category: 'unisex',
    garment: 'tee',
    tag: 'Bestseller',
    fabric: 'Handloom cotton, 180 gsm',
    desc: 'A heavier tee with a dropped shoulder and a neck that keeps its shape. Pre-washed, so what you buy is what stays.',
    colors: [
      { name: 'Chalk', hex: '#efe9df' },
      { name: 'Clay', hex: '#c98f73' },
      { name: 'Ink', hex: '#2d3240' }
    ],
    sizes: ['XS', 'S', 'M', 'L', 'XL'],
    soldOut: ['XS']
  },
  {
    id: 'loom-overshirt',
    name: 'Loom Overshirt',
    fig: 'Fig. 02',
    price: 3290,
    category: 'men',
    garment: 'overshirt',
    tag: 'New',
    fabric: 'Handloom cotton, 240 gsm',
    desc: 'Worn open over a tee or buttoned up as a shirt. Two patch pockets, corozo buttons, felled seams throughout.',
    colors: [
      { name: 'Oat', hex: '#c9a98a' },
      { name: 'Moss', hex: '#8e9677' },
      { name: 'Undyed', hex: '#e7dfcf' }
    ],
    sizes: ['S', 'M', 'L', 'XL'],
    soldOut: []
  },
  {
    id: 'pleated-trouser',
    name: 'Pleated Wide Trouser',
    fig: 'Fig. 03',
    price: 2790,
    category: 'women',
    garment: 'trouser',
    tag: '',
    fabric: 'Stonewashed linen, 185 gsm',
    desc: 'High rise, a single deep pleat and a leg that moves when you do. Side-adjusters instead of belt loops.',
    colors: [
      { name: 'Sand', hex: '#dccbb0' },
      { name: 'Charcoal', hex: '#4a4744' },
      { name: 'Lilac', hex: '#c8bfdc' }
    ],
    sizes: ['24', '26', '28', '30', '32'],
    soldOut: ['32']
  },
  {
    id: 'monsoon-dress',
    name: 'Monsoon Slip Dress',
    fig: 'Fig. 04',
    price: 3490,
    category: 'women',
    garment: 'dress',
    tag: 'Only 40 left',
    fabric: 'Hand-spun khadi, 160 gsm',
    desc: 'Cut on the bias so it falls without clinging. Adjustable straps; long enough to wear with sandals or sneakers.',
    colors: [
      { name: 'Rose clay', hex: '#dfb3a4' },
      { name: 'Indigo', hex: '#3d4a6b' },
      { name: 'Butter', hex: '#efdca4' }
    ],
    sizes: ['XS', 'S', 'M', 'L'],
    soldOut: []
  },
  {
    id: 'mandarin-kurta',
    name: 'Mandarin Kurta Shirt',
    fig: 'Fig. 05',
    price: 2490,
    category: 'men',
    garment: 'kurta',
    tag: '',
    fabric: 'Hand-spun khadi, 160 gsm',
    desc: 'Somewhere between a kurta and a shirt. Band collar, half placket, side slits, and a hidden pocket for your phone.',
    colors: [
      { name: 'Undyed', hex: '#ece3d2' },
      { name: 'Sage', hex: '#b7c2a6' },
      { name: 'Rust', hex: '#b26a4c' }
    ],
    sizes: ['S', 'M', 'L', 'XL', 'XXL'],
    soldOut: ['XXL']
  },
  {
    id: 'field-jacket',
    name: 'Field Chore Jacket',
    fig: 'Fig. 06',
    price: 4990,
    category: 'unisex',
    garment: 'jacket',
    tag: 'Limited',
    fabric: 'Double-weave handloom, 320 gsm',
    desc: 'Our heaviest piece. Four pockets, a ribbed hem and a notch collar you can flip up when the wind turns.',
    colors: [
      { name: 'Tobacco', hex: '#8a6a4f' },
      { name: 'Slate', hex: '#6f7a86' },
      { name: 'Ecru', hex: '#e2d6bf' }
    ],
    sizes: ['S', 'M', 'L', 'XL'],
    soldOut: ['S']
  },
  {
    id: 'linen-trouser',
    name: 'Drawstring Linen Pant',
    fig: 'Fig. 07',
    price: 2290,
    category: 'men',
    garment: 'trouser',
    tag: '',
    fabric: 'Stonewashed linen, 185 gsm',
    desc: 'The pant you will live in from April to October. Elastic back, flat drawcord, deep side pockets.',
    colors: [
      { name: 'Stone', hex: '#d6cdbd' },
      { name: 'Olive', hex: '#7d8161' },
      { name: 'Navy', hex: '#2f3a52' }
    ],
    sizes: ['S', 'M', 'L', 'XL'],
    soldOut: []
  }
];

/* The lookbook rail: one card per day. */
window.LOOKS = [
  { day: 'Mon', title: 'Studio day', garment: 'overshirt', color: '#c9a98a', bg: '#f3dccb', note: 'Overshirt, open, over the Everyday Tee.' },
  { day: 'Tue', title: 'Market run', garment: 'tee', color: '#c98f73', bg: '#f6e7c8', note: 'Clay tee, drawstring pant, chappals.' },
  { day: 'Wed', title: 'Rain, finally', garment: 'dress', color: '#3d4a6b', bg: '#dcd8ef', note: 'Indigo slip dress with the chore jacket.' },
  { day: 'Thu', title: 'Long lunch', garment: 'kurta', color: '#b7c2a6', bg: '#dfe9dc', note: 'Sage kurta shirt, sleeves rolled twice.' },
  { day: 'Fri', title: 'After dark', garment: 'jacket', color: '#6f7a86', bg: '#e6dde8', note: 'Slate jacket, collar up.' },
  { day: 'Sat', title: 'Nowhere to be', garment: 'trouser', color: '#c8bfdc', bg: '#f4d9dc', note: 'Lilac wide trouser, bare feet.' },
  { day: 'Sun', title: 'Laundry', garment: 'tee', color: '#efe9df', bg: '#e9efe4', note: 'Everything, washed, drying on the terrace.' }
];
