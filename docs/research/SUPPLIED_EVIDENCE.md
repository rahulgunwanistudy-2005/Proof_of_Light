# Evidence base for Proof of Light (verified 8 Nov 2026)

Use only these for claims in README, Devpost and video. Quote under 15 words per source; paraphrase otherwise.

## The problem: AI-faked damage evidence for refunds
- WIRED, "Scammers in China Are Using AI-Generated Images to Get Refunds" (Dec 2025): crab-seller case; a dozen+ RedNote seller posts; Forter: AI-doctored refund images up 15%+ since start of year; one ring filed $1M+ of claims with AI-altered crack/dent photos; seller-side AI chatbots unreliable at detection. https://www.wired.com/story/scammers-in-china-are-using-ai-generated-images-to-get-refunds/
- China Daily (4 Dec 2025): shopper given 8 days' administrative detention for AI-faked dead-crab images/videos. https://global.chinadaily.com.cn/a/202512/04/WS693171e0a310d6866eb2cee8.html
- China Daily (12/17 Dec 2025): small sellers hit; platform service centre "could not determine" whether images were AI. https://www.chinadailyhk.com/article/625283 , https://regional.chinadaily.com.cn/wic/2025-12/17/c_1147989.htm
- OECD AI Incidents Monitor: multiple logged incidents (Jul, Aug, Nov 2025). https://oecd.ai/en/incidents/2025-07-23-b9e6 , https://oecd.ai/en/incidents/2025-11-14-7dd0
- Shopifreaks (13 Jan 2026): eBay trading-card sellers report a spike in AI-faked damage photos. https://www.shopifreaks.com/ebay-sellers-warn-of-rising-ai-driven-refund-scams/
- Retail Gazette (Jun 2026), Forter data: AI-generated damage claims are the fastest-growing form of return abuse. https://www.retailgazette.co.uk/blog/2026/06/retailers-face-surge-in-ai-generated-fake-damage-claims-and-refund-scams/
- TechRadar (Forter): $1.5M returns-abuse operation over Christmas 2025 using AI-altered damage images. https://techradar.com/pro/ai-image-tools-a-game-changer-for-creativity-and-retails-multi-billion-dollar-abuse-problem
- Schneier on Security (30 Dec 2025) coverage. https://www.schneier.com/?p=71390
- Vendor-bias flag: Forter sells fraud detection; WIRED and China Daily are independent.

## Why PayPal sellers are exposed
- PayPal Seller Protection excludes "significantly not as described" claims. https://pep.paypal.com/legalhub/seller-protection
- MRC 2026 Global eCommerce Payments & Fraud Report (n=1,278): refund/policy abuse and first-party misuse rising; $82 average cost to handle a first-party misuse dispute. https://merchantriskcouncil.org/who-we-are/mrc-news/press-releases/2026/mrc-releases-2026-global-ecommerce-payments-fraud-report

## The mechanism's lineage
- iProov Flashmark: server-generated one-time colour sequence reflected from the face proves real-time presence; patented, for faces. https://www.iproov.com/biometric-encyclopedia/genuine-presence-assurance ; flash rate kept under 3/s for photosensitive epilepsy: https://www.iproov.com/blog/iproov-safeguards-for-people-with-photosensitive-epilepsy
- WCAG 2.3.1 Three Flashes or Below Threshold. https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold

## PayPal platform facts we rely on (re-check docs while building)
- Disputes API v1 (15 endpoints incl. sandbox-only adjudicate and require-evidence): https://developer.paypal.com/docs/api/customer-disputes/v1/
- Disputes sandbox testing (Resolution Center self-service seeding): https://developer.paypal.com/disputes/test-go-live
- Negative testing headers (PayPal-Mock-Response): https://developer.paypal.com/tools/sandbox/negative-testing/request-headers/
- Webhook simulator events can't be signature-verified: https://developer.paypal.com/api/rest/webhooks/simulator/
- Agent Toolkit dispute tools gap (list/get/accept only): https://github.com/paypal/agent-toolkit
- Sandbox webhook reliability threads: https://www.paypal-community.com/t5/Sandbox-Environment/Webhooks-not-firing-in-sandbox-mode-Simulator-works-fine/m-p/3031181

## Hackathon rules and judging
- Rules: https://paypalaihackathon.devpost.com/rules
- Video carries significant weight; judges may not run the project: https://paypalaihackathon.devpost.com/updates/47306-lights-camera-paypal-video-tips-and-how-judging-works
- Judges have no LLM keys; keep it free and up until 15 Dec: https://paypalaihackathon.devpost.com/forum_topics/45465-api-key-for-judges

## Crowd check (5 Nov 2026)
Among 1,013 public GitHub repos naming this hackathon: no light-challenge / liveness-for-objects mechanism. Nearest: Pay-on-Proof (LLM "signs of editing or AI" score), Holdfast (staff-captured rental damage photos), dispute desks (CaseClerk, DisputeDesk, Witness, Rebuttal). Outside the hackathon: Truepic controlled capture (SDK + device attestation) for insurance claims.
