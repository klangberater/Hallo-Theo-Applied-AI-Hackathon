// Fletcher — "Where the knowledge lives" deck.
// Paper palette + teal accent. Serif headings, sans body.

const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const {
  FaBalanceScale, FaArchive, FaBrain, FaFingerprint,
  FaQuoteLeft, FaCheckCircle, FaLock, FaArrowRight,
} = require("react-icons/fa");

// --------------------------------------------------------------------------
// Palette
// --------------------------------------------------------------------------
const C = {
  paper:        "F5F4F0",  // bg of regular slides
  paperDark:    "1C1917",  // text
  paperMid:     "44403C",  // body
  paperMute:    "78716C",  // captions
  paperBorder:  "E7E5E4",
  paperLight:   "FAFAF9",
  card:         "FFFFFF",

  teal:         "0D9488",  // primary accent
  tealDeep:     "115E59",  // title slide background + emphasis
  tealDark:     "134E4A",  // even deeper
  tealLight:    "CCFBF1",  // wash
  tealVeryLite: "F0FDFA",

  amber:        "B45309",  // for legal warnings / pattern emphasis
  amberLight:   "FEF3C7",
};

// Font stacks. Cambria + Calibri for solid Windows + Mac availability.
const FONT_SERIF = "Cambria";   // heading
const FONT_SANS  = "Calibri";   // body

// --------------------------------------------------------------------------
// Icon helper
// --------------------------------------------------------------------------
function svgFor(IconComponent, color = "#0D9488", size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}
async function iconPng(IconComponent, color = "#0D9488", size = 256) {
  const svg = svgFor(IconComponent, color, size);
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// --------------------------------------------------------------------------
// Reusable shadow factory (option objects mutate — never share refs)
// --------------------------------------------------------------------------
const softShadow = () => ({
  type: "outer", color: "000000", opacity: 0.08,
  blur: 12, offset: 3, angle: 90,
});

// --------------------------------------------------------------------------
// Slide chrome — applied to every non-title slide
// --------------------------------------------------------------------------
function paperBackground(slide) {
  slide.background = { color: C.paper };
}

function sectionHeader(slide, { kicker, title }) {
  // Kicker (small teal label)
  slide.addText(kicker, {
    x: 0.5, y: 0.38, w: 9, h: 0.28,
    fontFace: FONT_SANS, fontSize: 11, bold: true,
    color: C.teal, charSpacing: 3, margin: 0,
  });
  // Big serif heading
  slide.addText(title, {
    x: 0.5, y: 0.62, w: 9, h: 0.7,
    fontFace: FONT_SERIF, fontSize: 36, italic: true,
    color: C.paperDark, margin: 0,
  });
}

// Page-corner identifier ("L1 / 03")
function cornerStamp(slide, label) {
  slide.addText(label, {
    x: 8.7, y: 0.4, w: 1.0, h: 0.25,
    fontFace: FONT_SANS, fontSize: 9, bold: true,
    color: C.paperMute, charSpacing: 3, align: "right", margin: 0,
  });
}

// --------------------------------------------------------------------------
// MAIN
// --------------------------------------------------------------------------
async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = "Fletcher — Where the knowledge lives";
  pres.author = "Fletcher team";

  // Pre-render icons (sharp is async)
  const ic = {
    book:        await iconPng(FaBalanceScale,  "#FFFFFF", 256),
    bookDark:    await iconPng(FaBalanceScale,  "#0D9488", 256),
    folder:      await iconPng(FaArchive,       "#FFFFFF", 256),
    folderDark:  await iconPng(FaArchive,       "#0D9488", 256),
    brain:       await iconPng(FaBrain,         "#FFFFFF", 256),
    brainDark:   await iconPng(FaBrain,         "#0D9488", 256),
    lock:        await iconPng(FaLock,          "#0D9488", 256),
    fingerprint: await iconPng(FaFingerprint,   "#0D9488", 256),
    quote:       await iconPng(FaQuoteLeft,     "#0D9488", 256),
    check:       await iconPng(FaCheckCircle,   "#0D9488", 256),
    arrow:       await iconPng(FaArrowRight,    "#78716C", 256),
  };

  // ========================================================================
  // SLIDE 1 — Title
  // ========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.tealDeep };

    // Left teal slab is the whole background; add a paper-color sidebar
    // on the right with a quote-style accent. Single hero, no clutter.

    // Wordmark
    s.addText("Fletcher", {
      x: 0.7, y: 1.0, w: 8.0, h: 1.4,
      fontFace: FONT_SERIF, fontSize: 84, italic: true,
      color: "FFFFFF", margin: 0,
    });

    // Tagline
    s.addText("Where the knowledge lives.", {
      x: 0.78, y: 2.5, w: 8.5, h: 0.6,
      fontFace: FONT_SERIF, fontSize: 28, italic: true,
      color: C.tealLight, margin: 0,
    });

    // Subline
    s.addText(
      "An AI operations co-pilot for German property management — and how it thinks.",
      {
        x: 0.78, y: 3.15, w: 8.5, h: 0.45,
        fontFace: FONT_SANS, fontSize: 15,
        color: "A7F3D0", margin: 0,
      }
    );

    // Hairline divider
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.78, y: 3.75, w: 0.6, h: 0.02,
      fill: { color: "5EEAD4" }, line: { type: "none" },
    });

    // Author / context
    s.addText("Applied AI Hackathon · May 2026", {
      x: 0.78, y: 3.85, w: 8.5, h: 0.3,
      fontFace: FONT_SANS, fontSize: 11, bold: true,
      color: "5EEAD4", charSpacing: 3, margin: 0,
    });

    // Right-edge teardrop / motif: a small diamond grid of dots so the slide
    // isn't 100% flat. Subtle.
    for (let row = 0; row < 6; row++) {
      for (let col = 0; col < 3; col++) {
        s.addShape(pres.shapes.OVAL, {
          x: 8.3 + col * 0.35, y: 0.9 + row * 0.6,
          w: 0.08, h: 0.08,
          fill: { color: "14B8A6", transparency: 50 }, line: { type: "none" },
        });
      }
    }
  }

  // ========================================================================
  // SLIDE 2 — The problem (one breath of context before diving in)
  // ========================================================================
  {
    const s = pres.addSlide();
    paperBackground(s);
    sectionHeader(s, {
      kicker: "WHY THIS MATTERS",
      title: "It's not the volume — it's the context.",
    });
    cornerStamp(s, "01");

    s.addText(
      "Frau Köhler's heater fails for the sixth time this winter. The reply " +
      "needs her lease clause, her medical attestation, the vendor history, " +
      "the BGB section, the open offer from Bergmann, and what Jonas " +
      "pre-approved last Friday. All of that lives in different places.",
      {
        x: 0.5, y: 1.7, w: 9, h: 1.3,
        fontFace: FONT_SANS, fontSize: 18,
        color: C.paperDark, lineSpacingMultiple: 1.35, margin: 0,
      }
    );

    // Three small "where it lives" callouts
    const places = [
      { label: "Lease PDF",         where: "owner's drive" },
      { label: "Vendor invoices",   where: "PMS system" },
      { label: "Slack approvals",   where: "team chat"   },
      { label: "BGB / BetrKV",      where: "legal docs"   },
      { label: "Past tickets",      where: "memory only"  },
    ];
    const cardW = 1.7, cardH = 0.85, gap = 0.12;
    const totalW = places.length * cardW + (places.length - 1) * gap;
    const startX = (10 - totalW) / 2;

    places.forEach((p, i) => {
      const x = startX + i * (cardW + gap);
      const y = 3.5;
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: cardH,
        fill: { color: C.card }, line: { color: C.paperBorder, width: 0.5 },
        shadow: softShadow(),
      });
      s.addText(p.label, {
        x: x + 0.12, y: y + 0.10, w: cardW - 0.24, h: 0.3,
        fontFace: FONT_SANS, fontSize: 11, bold: true,
        color: C.paperDark, margin: 0,
      });
      s.addText(p.where, {
        x: x + 0.12, y: y + 0.4, w: cardW - 0.24, h: 0.3,
        fontFace: FONT_SANS, fontSize: 9.5,
        color: C.paperMute, italic: true, margin: 0,
      });
    });

    // Closing line
    s.addText(
      "Fletcher's job is to hold all of it — and to remember.",
      {
        x: 0.5, y: 4.7, w: 9, h: 0.4,
        fontFace: FONT_SERIF, fontSize: 18, italic: true,
        color: C.teal, align: "center", margin: 0,
      }
    );
  }

  // ========================================================================
  // SLIDE 3 — Three stores at a glance
  // ========================================================================
  {
    const s = pres.addSlide();
    paperBackground(s);
    sectionHeader(s, {
      kicker: "THE ARCHITECTURE OF MEMORY",
      title: "Three deliberate stores. One question each.",
    });
    cornerStamp(s, "02");

    const stores = [
      {
        tag: "L1",
        title: "The Rulebook",
        q: "What applies?",
        body: "Laws, internal policies, reply templates. Same for every tenant. Rarely changes.",
        icon: ic.book,
      },
      {
        tag: "L2",
        title: "The Filing Cabinet",
        q: "What is true right now?",
        body: "Tenants, leases, units, tickets, invoices, vendors — the live state of the business.",
        icon: ic.folder,
      },
      {
        tag: "L3",
        title: "The Memory",
        q: "What have we learned?",
        body: "Patterns derived from every past message — the contextual knowledge a 20-year manager has in their head.",
        icon: ic.brain,
      },
    ];

    const cardW = 2.95, cardH = 3.5, gap = 0.18;
    const totalW = stores.length * cardW + (stores.length - 1) * gap;
    const startX = (10 - totalW) / 2;

    stores.forEach((store, i) => {
      const x = startX + i * (cardW + gap);
      const y = 1.55;

      // Card
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: cardH,
        fill: { color: C.card }, line: { color: C.paperBorder, width: 0.5 },
        shadow: softShadow(),
      });

      // Top accent bar — teal
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: 0.08,
        fill: { color: C.teal }, line: { type: "none" },
      });

      // Icon circle
      s.addShape(pres.shapes.OVAL, {
        x: x + cardW / 2 - 0.45, y: y + 0.45, w: 0.9, h: 0.9,
        fill: { color: C.teal }, line: { type: "none" },
      });
      s.addImage({
        data: store.icon,
        x: x + cardW / 2 - 0.25, y: y + 0.65, w: 0.5, h: 0.5,
      });

      // Tag (L1 / L2 / L3)
      s.addText(store.tag, {
        x: x + 0.18, y: y + 0.22, w: 0.6, h: 0.3,
        fontFace: FONT_SANS, fontSize: 10, bold: true,
        color: C.teal, charSpacing: 4, margin: 0,
      });

      // Title
      s.addText(store.title, {
        x: x + 0.2, y: y + 1.55, w: cardW - 0.4, h: 0.45,
        fontFace: FONT_SERIF, fontSize: 22, italic: true,
        color: C.paperDark, align: "center", margin: 0,
      });

      // The question (italic, accent color)
      s.addText('"' + store.q + '"', {
        x: x + 0.2, y: y + 2.05, w: cardW - 0.4, h: 0.35,
        fontFace: FONT_SERIF, fontSize: 14, italic: true,
        color: C.teal, align: "center", margin: 0,
      });

      // Body
      s.addText(store.body, {
        x: x + 0.3, y: y + 2.5, w: cardW - 0.6, h: 0.9,
        fontFace: FONT_SANS, fontSize: 11.5,
        color: C.paperMid, align: "center",
        lineSpacingMultiple: 1.3, margin: 0,
      });
    });
  }

  // ========================================================================
  // Helper for the L1/L2/L3 detail slides — consistent layout.
  // ========================================================================
  function layerSlide({
    tag, kicker, title, question, intro, examples,
    techNote, iconPng, cornerLabel, emphasis,
  }) {
    const s = pres.addSlide();
    paperBackground(s);
    cornerStamp(s, cornerLabel);

    // Kicker
    s.addText(kicker, {
      x: 0.5, y: 0.38, w: 9, h: 0.28,
      fontFace: FONT_SANS, fontSize: 11, bold: true,
      color: C.teal, charSpacing: 3, margin: 0,
    });

    // Title row — circle icon + tag + serif title
    s.addShape(pres.shapes.OVAL, {
      x: 0.5, y: 0.66, w: 0.7, h: 0.7,
      fill: { color: C.teal }, line: { type: "none" },
    });
    s.addImage({
      data: iconPng,
      x: 0.65, y: 0.81, w: 0.4, h: 0.4,
    });
    s.addText(tag, {
      x: 1.35, y: 0.66, w: 0.7, h: 0.32,
      fontFace: FONT_SANS, fontSize: 11, bold: true,
      color: C.teal, charSpacing: 4, margin: 0,
    });
    s.addText(title, {
      x: 1.35, y: 0.92, w: 8, h: 0.5,
      fontFace: FONT_SERIF, fontSize: 28, italic: true,
      color: C.paperDark, margin: 0,
    });

    // The question
    s.addText('"' + question + '"', {
      x: 0.5, y: 1.6, w: 9, h: 0.4,
      fontFace: FONT_SERIF, fontSize: 16, italic: true,
      color: C.teal, margin: 0,
    });

    // Intro paragraph
    s.addText(intro, {
      x: 0.5, y: 2.05, w: 9, h: 0.7,
      fontFace: FONT_SANS, fontSize: 13,
      color: C.paperMid, lineSpacingMultiple: 1.35, margin: 0,
    });

    // Examples card on left
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 2.95, w: 5.7, h: 2.3,
      fill: { color: C.card }, line: { color: C.paperBorder, width: 0.5 },
      shadow: softShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 2.95, w: 0.06, h: 2.3,
      fill: { color: C.teal }, line: { type: "none" },
    });
    s.addText("EXAMPLES", {
      x: 0.75, y: 3.08, w: 5.3, h: 0.25,
      fontFace: FONT_SANS, fontSize: 9, bold: true,
      color: C.paperMute, charSpacing: 3, margin: 0,
    });
    s.addText(
      examples.map((e, i) => ({
        text: e,
        options: { bullet: { code: "25CF" }, breakLine: i < examples.length - 1 },
      })),
      {
        x: 0.85, y: 3.35, w: 5.2, h: 1.85,
        fontFace: FONT_SANS, fontSize: 11.5,
        color: C.paperDark, paraSpaceAfter: 4, margin: 0,
      }
    );

    // Right column: emphasis quote + tech note
    if (emphasis) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: 6.4, y: 2.95, w: 3.1, h: 1.5,
        fill: { color: C.tealVeryLite }, line: { color: C.tealLight, width: 0.5 },
      });
      s.addImage({
        data: ic.quote, x: 6.55, y: 3.05, w: 0.22, h: 0.22,
      });
      s.addText(emphasis, {
        x: 6.55, y: 3.32, w: 2.85, h: 1.0,
        fontFace: FONT_SERIF, fontSize: 12, italic: true,
        color: C.tealDeep, lineSpacingMultiple: 1.3, margin: 0,
      });
    }

    // Tech note pill (right column lower)
    s.addText("UNDER THE HOOD", {
      x: 6.4, y: 4.6, w: 3.1, h: 0.22,
      fontFace: FONT_SANS, fontSize: 9, bold: true,
      color: C.paperMute, charSpacing: 3, margin: 0,
    });
    s.addText(techNote, {
      x: 6.4, y: 4.85, w: 3.1, h: 0.45,
      fontFace: FONT_SANS, fontSize: 10.5,
      color: C.paperMid, italic: true,
      lineSpacingMultiple: 1.25, margin: 0,
    });

    return s;
  }

  // ========================================================================
  // SLIDE 4 — L1 The Rulebook
  // ========================================================================
  layerSlide({
    tag: "L1",
    cornerLabel: "03",
    kicker: "STORE ONE",
    title: "The Rulebook",
    question: "What applies — by law, by policy, by template?",
    intro:
      "Things that are the same for every tenant and every property, and rarely change. Fletcher quotes from here verbatim — it never invents legal references.",
    examples: [
      "BGB § 535 (landlord duty to maintain), § 536 (rent reduction), § 556 (operating-cost statements)",
      "BetrKV — which operating costs are passable to tenants",
      "Internal policies — 4-hour response window for heating outages, escalation thresholds",
      "Reply templates — defect acknowledgement, document request, appointment confirmation",
    ],
    techNote:
      "Markdown files in the repository. Full-text search via BM25. Versioned in git like a living manual.",
    iconPng: ic.book,
    emphasis:
      "Every legal citation in a Fletcher reply traces back to a specific clause in this store. If the rule isn't here, Fletcher won't claim it.",
  });

  // ========================================================================
  // SLIDE 5 — L2 Filing Cabinet
  // ========================================================================
  layerSlide({
    tag: "L2",
    cornerLabel: "04",
    kicker: "STORE TWO",
    title: "The Filing Cabinet",
    question: "What is the current state of the world?",
    intro:
      "Every hard operational fact — the things you could keep in a spreadsheet, but kept in a real database. Updated transactionally and audit-grade.",
    examples: [
      "Properties + units — Zossener Str. 47, WE 4 left, 68 sqm, owner Wegener",
      "Tenants + leases — Frau Köhler, since 1997, 612 € cold rent, medical attestation in Anlage 3",
      "Tickets — every past case, dates, costs, vendor notes",
      "Invoices + open offers — Bergmann offer for 372 € pending since April",
      "Conversations — every WhatsApp, email, internal Slack thread",
    ],
    techNote:
      "PostgreSQL with ~15 tables, isolated under the `theo` schema. Classic CRM/PMS structure.",
    iconPng: ic.folder,
    emphasis:
      "Opening a ticket instantly surfaces the tenant card, lease status, and full history. No tab-switching, no manual lookup.",
  });

  // ========================================================================
  // SLIDE 6 — L3 The Memory (the moat)
  // ========================================================================
  layerSlide({
    tag: "L3",
    cornerLabel: "05",
    kicker: "STORE THREE · THE DIFFERENTIATOR",
    title: "The Memory",
    question: "What have we learned about this person, this unit, this vendor?",
    intro:
      "Not facts — learned patterns. Fletcher reads every conversation and ticket and extracts durable statements with validity periods and source citations. Nobody types these in; they emerge.",
    examples: [
      '"Frau Köhler has heightened cold sensitivity after her hip surgery — valid since 18.05.2024."',
      '"The living-room radiator in WE 4 left has shown recurring failure for 18 months — same root cause (thermostat valve)."',
      '"Anja Köhler represents her mother Margarethe legally."',
      '"Bergmann submitted an offer in April 2025 — still unapproved after 7 months."',
    ],
    techNote:
      "Knowledge graph in Neo4j, continuously fed by Graphiti. Every claim is time-bounded and source-cited.",
    iconPng: ic.brain,
    emphasis:
      "This is the contextual knowledge a 20-year property manager carries in their head — externalised, queryable, and never forgotten.",
  });

  // ========================================================================
  // SLIDE 7 — Walkthrough: Frau Köhler heating message
  // The deck's strongest moment. Numbered flow across the slide.
  // ========================================================================
  {
    const s = pres.addSlide();
    paperBackground(s);
    cornerStamp(s, "06");

    s.addText("WORKED EXAMPLE", {
      x: 0.5, y: 0.38, w: 9, h: 0.28,
      fontFace: FONT_SANS, fontSize: 11, bold: true,
      color: C.teal, charSpacing: 3, margin: 0,
    });
    s.addText("How the three stores combine — in seconds.", {
      x: 0.5, y: 0.62, w: 9, h: 0.7,
      fontFace: FONT_SERIF, fontSize: 30, italic: true,
      color: C.paperDark, margin: 0,
    });

    // The incoming WhatsApp — chat bubble style
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 1.55, w: 4.2, h: 1.1,
      fill: { color: "DCFCE7" },  // light green WhatsApp-ish
      line: { type: "none" },
    });
    s.addText("MARGARETHE KÖHLER · WhatsApp · just now", {
      x: 0.7, y: 1.65, w: 3.9, h: 0.25,
      fontFace: FONT_SANS, fontSize: 9, bold: true,
      color: "047857", charSpacing: 2, margin: 0,
    });
    s.addText(
      '"Die Heizung im Wohnzimmer geht schon wieder nicht."',
      {
        x: 0.7, y: 1.93, w: 3.9, h: 0.7,
        fontFace: FONT_SERIF, fontSize: 14, italic: true,
        color: C.paperDark, margin: 0,
      }
    );

    // Big "→ within seconds" callout
    s.addImage({ data: ic.arrow, x: 4.85, y: 1.95, w: 0.3, h: 0.3 });
    s.addText("within seconds", {
      x: 4.7, y: 2.3, w: 0.7, h: 0.25,
      fontFace: FONT_SANS, fontSize: 9, italic: true,
      color: C.paperMute, align: "center", margin: 0,
    });

    // Four numbered query steps, stacked vertically on right
    const steps = [
      {
        n: "1", tag: "L2",
        what: 'Who is this phone number?',
        result: "Margarethe Köhler · WE 4 left · lease since 1997 · open Bergmann offer.",
      },
      {
        n: "2", tag: "L3",
        what: "What do we know about her?",
        result: "5 prior heating cases · successful rent reduction in February · post-op cold sensitivity · daughter is a lawyer.",
      },
      {
        n: "3", tag: "L1",
        what: "What does the law require?",
        result: "BGB § 535 · 4-hour response window during heating season.",
      },
      {
        n: "4", tag: "L2",
        what: "Any internal pre-approvals?",
        result: "Yes — Jonas Petersen pre-approved 500 € last Friday.",
      },
    ];

    const stepX = 5.4, stepW = 4.1;
    let stepY = 1.55;
    const stepH = 0.83;
    steps.forEach((step, i) => {
      // Number circle
      s.addShape(pres.shapes.OVAL, {
        x: stepX, y: stepY + 0.08, w: 0.42, h: 0.42,
        fill: { color: C.teal }, line: { type: "none" },
      });
      s.addText(step.n, {
        x: stepX, y: stepY + 0.06, w: 0.42, h: 0.45,
        fontFace: FONT_SERIF, fontSize: 16, bold: true,
        color: "FFFFFF", align: "center", valign: "middle", margin: 0,
      });

      // Tag pill
      s.addShape(pres.shapes.RECTANGLE, {
        x: stepX + 0.55, y: stepY + 0.05, w: 0.32, h: 0.22,
        fill: { color: C.tealLight }, line: { type: "none" },
      });
      s.addText(step.tag, {
        x: stepX + 0.55, y: stepY + 0.06, w: 0.32, h: 0.22,
        fontFace: FONT_SANS, fontSize: 8, bold: true,
        color: C.tealDeep, align: "center", valign: "middle",
        charSpacing: 2, margin: 0,
      });

      // Question text
      s.addText(step.what, {
        x: stepX + 0.95, y: stepY + 0.0, w: stepW - 0.95, h: 0.3,
        fontFace: FONT_SANS, fontSize: 11, bold: true,
        color: C.paperDark, margin: 0,
      });

      // Result text
      s.addText(step.result, {
        x: stepX + 0.95, y: stepY + 0.32, w: stepW - 0.95, h: 0.5,
        fontFace: FONT_SANS, fontSize: 10,
        color: C.paperMid, lineSpacingMultiple: 1.2, margin: 0,
      });

      stepY += stepH;
    });

    // Bottom synthesis line
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 5.1, w: 4.2, h: 0.32,
      fill: { color: C.tealDeep }, line: { type: "none" },
    });
    s.addText(
      "→ One reply, fully cited. Drafted in ≈ 30s.",
      {
        x: 0.5, y: 5.1, w: 4.2, h: 0.32,
        fontFace: FONT_SANS, fontSize: 11, bold: true,
        color: "FFFFFF", align: "center", valign: "middle", margin: 0,
      }
    );

    // Tagline
    s.addText(
      "Every single claim in that reply traces back to a specific row, " +
      "fact, or paragraph. No invention.",
      {
        x: 0.5, y: 4.65, w: 4.2, h: 0.4,
        fontFace: FONT_SERIF, fontSize: 11, italic: true,
        color: C.paperMid, lineSpacingMultiple: 1.25, margin: 0,
      }
    );
  }

  // ========================================================================
  // SLIDE 8 — Why three storage layers (comparison table)
  // ========================================================================
  {
    const s = pres.addSlide();
    paperBackground(s);
    sectionHeader(s, {
      kicker: "DESIGN PRINCIPLE",
      title: "Why three stores, not one database.",
    });
    cornerStamp(s, "07");

    s.addText(
      "Different questions need different shapes of memory. Forcing all three " +
      "into one database would mean Fletcher would fail at one of them — " +
      "usually whichever one a competitor isn't doing yet.",
      {
        x: 0.5, y: 1.55, w: 9, h: 0.7,
        fontFace: FONT_SANS, fontSize: 13,
        color: C.paperMid, lineSpacingMultiple: 1.35, margin: 0,
      }
    );

    // Comparison table
    const rows = [
      {
        store: "L1", q: "What applies?",
        why: "Rarely written, often read. Versioned like a book.",
        tech: "Markdown + BM25",
      },
      {
        store: "L2", q: "What is true now?",
        why: "Must be exact, transactional, auditable. A relational database.",
        tech: "PostgreSQL",
      },
      {
        store: "L3", q: "What did we learn?",
        why: "Must surface patterns across time. A graph database.",
        tech: "Neo4j + Graphiti",
      },
    ];

    const tableY = 2.4;
    const rowH = 0.72;
    const cols = [
      { x: 0.5, w: 0.85, label: "STORE" },
      { x: 1.4, w: 1.9, label: "QUESTION" },
      { x: 3.4, w: 4.4, label: "WHY ITS OWN STORE" },
      { x: 7.9, w: 1.7, label: "TECH" },
    ];

    // Header row
    cols.forEach(c => {
      s.addText(c.label, {
        x: c.x, y: tableY, w: c.w, h: 0.32,
        fontFace: FONT_SANS, fontSize: 9, bold: true,
        color: C.paperMute, charSpacing: 3, margin: 0,
      });
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: tableY + 0.32, w: 9.1, h: 0.015,
      fill: { color: C.paperBorder }, line: { type: "none" },
    });

    // Rows
    rows.forEach((r, i) => {
      const y = tableY + 0.45 + i * rowH;
      // alternating row tint (subtle)
      if (i % 2 === 1) {
        s.addShape(pres.shapes.RECTANGLE, {
          x: 0.5, y, w: 9.1, h: rowH,
          fill: { color: C.paperLight }, line: { type: "none" },
        });
      }
      // Store tag — teal pill
      s.addShape(pres.shapes.RECTANGLE, {
        x: cols[0].x, y: y + 0.2, w: 0.55, h: 0.3,
        fill: { color: C.teal }, line: { type: "none" },
      });
      s.addText(r.store, {
        x: cols[0].x, y: y + 0.19, w: 0.55, h: 0.32,
        fontFace: FONT_SANS, fontSize: 11, bold: true,
        color: "FFFFFF", align: "center", valign: "middle",
        charSpacing: 2, margin: 0,
      });
      // Question
      s.addText('"' + r.q + '"', {
        x: cols[1].x, y: y + 0.18, w: cols[1].w, h: 0.5,
        fontFace: FONT_SERIF, fontSize: 12.5, italic: true,
        color: C.paperDark, valign: "middle", margin: 0,
      });
      // Why
      s.addText(r.why, {
        x: cols[2].x, y: y + 0.18, w: cols[2].w, h: 0.5,
        fontFace: FONT_SANS, fontSize: 11,
        color: C.paperMid, valign: "middle",
        lineSpacingMultiple: 1.25, margin: 0,
      });
      // Tech
      s.addText(r.tech, {
        x: cols[3].x, y: y + 0.18, w: cols[3].w, h: 0.5,
        fontFace: FONT_SANS, fontSize: 11, bold: true,
        color: C.tealDeep, valign: "middle", margin: 0,
      });
    });

    // Bottom emphasis line
    s.addText(
      "Each store does exactly what it was built for. None of them imitate the others.",
      {
        x: 0.5, y: 5.2, w: 9, h: 0.35,
        fontFace: FONT_SERIF, fontSize: 13, italic: true,
        color: C.teal, align: "center", margin: 0,
      }
    );
  }

  // ========================================================================
  // SLIDE 9 — Privacy & control
  // ========================================================================
  {
    const s = pres.addSlide();
    paperBackground(s);
    sectionHeader(s, {
      kicker: "TRUST",
      title: "Privacy and control, by design.",
    });
    cornerStamp(s, "08");

    const policies = [
      {
        tag: "L1",
        title: "Holds no tenant data.",
        body: "Just laws, internal rules, templates. Generic by design — nothing personal lives here.",
      },
      {
        tag: "L2",
        title: "Treated as operational data.",
        body: "Same controls as any property database — access policies, audit trails, retention rules.",
      },
      {
        tag: "L3",
        title: "Fully deletable on request.",
        body: "Every derived claim about a person can be removed alongside its source rows — GDPR-compliant.",
      },
    ];

    const cardW = 2.95, cardH = 2.65, gap = 0.18;
    const totalW = policies.length * cardW + (policies.length - 1) * gap;
    const startX = (10 - totalW) / 2;

    policies.forEach((p, i) => {
      const x = startX + i * (cardW + gap);
      const y = 1.75;

      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: cardH,
        fill: { color: C.card }, line: { color: C.paperBorder, width: 0.5 },
        shadow: softShadow(),
      });
      s.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 0.06, h: cardH,
        fill: { color: C.teal }, line: { type: "none" },
      });

      s.addShape(pres.shapes.RECTANGLE, {
        x: x + 0.3, y: y + 0.3, w: 0.5, h: 0.28,
        fill: { color: C.tealLight }, line: { type: "none" },
      });
      s.addText(p.tag, {
        x: x + 0.3, y: y + 0.3, w: 0.5, h: 0.28,
        fontFace: FONT_SANS, fontSize: 10, bold: true,
        color: C.tealDeep, align: "center", valign: "middle",
        charSpacing: 2, margin: 0,
      });

      s.addText(p.title, {
        x: x + 0.3, y: y + 0.75, w: cardW - 0.6, h: 0.7,
        fontFace: FONT_SERIF, fontSize: 17, italic: true,
        color: C.paperDark, lineSpacingMultiple: 1.15, margin: 0,
      });
      s.addText(p.body, {
        x: x + 0.3, y: y + 1.55, w: cardW - 0.6, h: 1.0,
        fontFace: FONT_SANS, fontSize: 11.5,
        color: C.paperMid, lineSpacingMultiple: 1.3, margin: 0,
      });
    });

    // Footer principle
    s.addImage({ data: ic.fingerprint, x: 0.5, y: 4.7, w: 0.35, h: 0.35 });
    s.addText(
      "Every recommendation Fletcher makes carries a source. Every source is traceable. Nothing in the shadows.",
      {
        x: 0.95, y: 4.65, w: 8.5, h: 0.6,
        fontFace: FONT_SERIF, fontSize: 14, italic: true,
        color: C.paperDark, lineSpacingMultiple: 1.3, margin: 0,
      }
    );
  }

  // ========================================================================
  // SLIDE 10 — Closing
  // ========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.tealDeep };

    // Wordmark, small, top-left
    s.addText("Fletcher", {
      x: 0.7, y: 0.55, w: 3, h: 0.5,
      fontFace: FONT_SERIF, fontSize: 26, italic: true,
      color: "FFFFFF", margin: 0,
    });

    // Big closing line
    s.addText(
      '"The contextual knowledge a 20-year property manager carries in their head — externalised, queryable, and never forgotten."',
      {
        x: 0.9, y: 1.75, w: 8.2, h: 2.0,
        fontFace: FONT_SERIF, fontSize: 30, italic: true,
        color: "FFFFFF", lineSpacingMultiple: 1.25, margin: 0,
      }
    );

    // Hairline
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.9, y: 3.9, w: 0.6, h: 0.02,
      fill: { color: "5EEAD4" }, line: { type: "none" },
    });

    // Subline
    s.addText("Three stores. One co-pilot. Zero invented citations.", {
      x: 0.9, y: 4.0, w: 8.2, h: 0.45,
      fontFace: FONT_SANS, fontSize: 16, bold: true,
      color: "5EEAD4", margin: 0,
    });

    // Footer
    s.addText("getfletcher.ai · built at the Applied AI Hackathon, May 2026", {
      x: 0.9, y: 5.1, w: 8.2, h: 0.3,
      fontFace: FONT_SANS, fontSize: 10,
      color: "99F6E4", italic: true, margin: 0,
    });

    // Same diamond grid motif as title slide
    for (let row = 0; row < 6; row++) {
      for (let col = 0; col < 3; col++) {
        s.addShape(pres.shapes.OVAL, {
          x: 8.3 + col * 0.35, y: 0.9 + row * 0.6,
          w: 0.08, h: 0.08,
          fill: { color: "14B8A6", transparency: 50 }, line: { type: "none" },
        });
      }
    }
  }

  // ========================================================================
  await pres.writeFile({
    fileName:
      "/Users/alexandergrosse/GitHub/Hallo-Theo-Applied-AI-Hackathon/docs/fletcher-data-layers.pptx",
  });
  console.log("wrote fletcher-data-layers.pptx");
}

main().catch((e) => { console.error(e); process.exit(1); });
