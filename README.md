# 📸 Photo Ops Suite
**Photo Ops Suite** is a growing collection of practical planning tools built specifically for wedding photographers.

It’s designed to help photographers create realistic timelines, plan around sunset and golden hour, and estimate post-processing workload, all with real-world wedding logistics in mind.

Built with Python and Streamlit, Photo Ops Suite focuses on clarity, speed, and photographer-aware planning rather than rigid schedules or generic event tools.

![Screenshot of Timeline Builder](assets/photo-ops-suite.webp)

## ✨ Why Photo Ops Suite Exists
Wedding photographers constantly juggle:
- Coverage limits  
- Portrait priorities  
- Travel time  
- Light conditions  
- Family dynamics  
- Post-processing workload  

Most existing tools are either too generic or not built for photographers.

Photo Ops Suite is built *by* a wedding photographer *for* wedding photographers to reflect how wedding days actually run, not how they look in a perfectly optimized spreadsheet.

## 🧰 Included Tools
### Wedding Day Timeline Builder
A comprehensive timeline planning tool that helps photographers:

- Build a full wedding day timeline from coverage start to end
- Account for:
  - First look vs. no first look
  - Family dynamics (divorced parents, strained relationships, etc.)
  - Realistic buffers and travel time
- Automatically:
  - Warn when timelines exceed coverage
  - Flag tight or unrealistic portrait windows
  - Show which blocks consume the most coverage time
- Export timelines as:
  - CSV files
  - Clean, copy-paste text versions

**Why does this matter?**  
This helps photographers plan confidently, set realistic expectations with couples and planners, and avoid over-promising coverage.

### Sunset, Golden Hour & Blue Hour Checker
A location-aware sunset planning tool designed with wedding days in mind.

- Search by:
  - Venue name
  - City/state
  - Full street address,
  - Pr manual latitude/longitude
- Automatically calculates:
  - Sunset
  - Golden hour
  - Blue hour

**Why does this matter?**  
This makes it easy to plan sunset portraits, advise couples on timing, and protect golden hour without guesswork.

### Post-Processing Time Calculator
A workload estimation tool for photographers who want realistic editing expectations.
- Estimate editing time based on:
  - Number of delivered images
  - Average time per photo
- Quickly understand:
  - Total editing hours
  - Realistic delivery timelines
- Useful for:
  - Internal workload planning
  - Setting client expectations
  - Avoiding burnout during busy seasons

**Why does this matter?**  
This supports sustainable workflows and clearer turnaround communication.

### Wedding Cost of Doing Business (CODB) Calculator
A wedding-specific pricing and sustainability tool designed to answer a critical question:

> *“What do I actually need to charge per wedding to make this business sustainable?”*

This tool helps photographers:

- Calculate true cost per wedding, including:
  - Annual fixed business expenses
  - Average per-wedding variable costs
  - Gear replacement and depreciation
- Account for time spent per wedding, including:
  - Pre-wedding communication and planning
  - Wedding day coverage and travel
  - Culling, editing, delivery, and follow-up
- Model tax-aware take-home income, using an estimated effective tax rate
- See:
  - Break-even price per wedding
  - Recommended pricing based on profit margin goals
  - Effective hourly rate at current pricing
  - How many weddings are needed to hit income goals

**Why does this matter?**  
Many wedding photographers underprice not because of skill — but because they underestimate time, costs, and taxes.  
This tool provides clarity, confidence, and data-backed pricing decisions.

## Design Philosophy
Photo Ops Suite is built around a few core principles:

- **Planning, not promises**  
  Wedding days *flex*. This tool supports smart planning, not rigid schedules.

- **Photographer-aware defaults**  
  Buffers, portrait blocks, and warnings reflect real wedding experiences.

- **Fast visual clarity**  
  Key information (sunset, coverage limits, time sinks) is surfaced immediately.

- **Modular & extensible**  
  New tools can be added without disrupting existing workflows.

## 🛠️ Tech Stack
- Python
- Streamlit
- Pandas
- SunriseSunset.io
- Open-Meteo & OpenStreetMap