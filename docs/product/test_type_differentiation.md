# Test Type Differentiation

This document records the P1-001 product boundary: each consumer research test type must use a distinct simulation profile instead of relying only on prompt wording.

## Concept Test

Concept Test stays closest to the legacy baseline. It emphasizes consumer resonance, clarity, and misinterpretation risk. The generic perception and decision paths remain available so existing concept-test behavior stays stable.

## Copy Test

Copy Test uses copy element attention. The perception layer scores headline, body, and CTA independently so reporting can separate initial hook, proof strength, and action clarity.

## Packaging Test

Packaging Test uses a visual attention model. The perception layer produces a text-based heatmap for color, layout, imagery, and text, and marks shelf context as simulated. This gives packaging work a real perception-layer signal rather than only a packaging prompt.

## A/B Test

A/B Test uses a paired comparison decision frame. Variants receive relative scores, a preference ranking, and a choice-set independence marker so the result can discuss preference strength rather than a single generic reaction.

## Price Test

Price Test uses a simplified Gabor-Granger decision model. Agents are assigned high, medium, or low price sensitivity, then current price is compared to a reference price to estimate acceptance probability and a price elasticity signal.

## Product Reporting Contract

Reports should surface the active `test_type_profile`, `perception_signals`, and `decision_signals` from each snapshot. For example, Price Test reports should include price sensitivity and willingness-to-pay interpretation; Packaging Test reports should include visual attention and shelf stand-out interpretation.