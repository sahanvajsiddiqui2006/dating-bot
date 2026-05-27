# Smart Calculator App Roadmap (Hindi)

## App Vision
Ek **all-in-one calculator app** jo simple math se lekar science, education, unit conversion, aur AI question solving support kare.

## Core Features
1. **Simple Calculator**
   - Add, Subtract, Multiply, Divide
   - Percentage, Brackets, Memory

2. **Scientific Calculator**
   - Trigonometry (sin, cos, tan)
   - log, ln, power, root, factorial
   - Degree/Radian mode

3. **Education Tools**
   - Algebra solver
   - Equation balance helper
   - Basic physics formulas (speed, force, density)
   - Chemistry molar mass helper

4. **Converters**
   - Length, weight, temperature
   - Currency (API based)
   - Time and data-size conversion

5. **AI Question Solver**
   - User question type kare -> step-by-step answer
   - Photo upload kare (OCR + Math parser)
   - Final answer + explanation mode

6. **History + Favorites**
   - Sare calculations auto-save
   - Important calculations pin/favorite

## Subscription Feature (Monthly 199)
- Free plan me:
  - Basic/simple calculator free
  - Limited AI solves per day
- Pro plan ₹199/month:
  - Unlimited AI solve
  - Photo solve high accuracy
  - No ads
  - Advanced science modules

## Add/Remove Subscription Logic
- App me "Upgrade to Pro" button.
- Google Play Billing use karke monthly plan **₹199**.
- Cancel/Remove ke liye:
  - User Google Play > Payments & subscriptions > Subscriptions > App > Cancel.
  - Cancel ke baad current billing cycle tak pro active rahega.

## Suggested Tech Stack
- **Frontend:** Flutter (Android-first, later iOS)
- **State:** Riverpod / Bloc
- **Local DB:** Hive / SQLite
- **Cloud:** Firebase (Auth + Firestore + Analytics)
- **AI Backend:** Python FastAPI + OCR (Tesseract/Google Vision) + Math solver pipeline
- **Payments:** Google Play Billing Library

## Play Store Upload Checklist
1. Google Play Developer account create kare.
2. Unique package name set kare.
3. Signed release AAB build kare.
4. App icon, screenshots, feature graphic ready kare.
5. Privacy Policy URL add kare.
6. Data safety form fill kare.
7. Content rating complete kare.
8. Internal testing -> closed testing -> production release.

## MVP Delivery Phases
- **Phase 1 (2-3 weeks):** Simple + scientific calculator + history.
- **Phase 2 (2 weeks):** Converters + education formula modules.
- **Phase 3 (3-4 weeks):** AI text solver + OCR photo solver.
- **Phase 4 (1 week):** Billing (₹199), ads toggle, Play Store release prep.

## Next Implementation Step
`Flutter starter project` ke saath:
- Home tabs: Simple | Scientific | AI Solve | History
- Pro paywall screen
- Billing integration stub
