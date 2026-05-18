package layout

import (
	"math"
	"regexp"
	"strings"
)

func Classify(f map[string]float64) (string, float64) {
	ink := f["ink_density"]
	edge := f["edge_density"]
	std := f["gray_std"]
	hline := f["hline_density"]
	vline := f["vline_density"]
	balance := f["line_balance"]
	signature := f["component_signature_score"]
	darkLight := f["luma_dark_light_ratio"]
	mid := f["luma_mid_fraction"]
	entropy := f["luma_hist_entropy"]

	scores := map[string]float64{
		LabelText:      1.5*ink + 0.6*entropy + 0.2 - 0.8*balance,
		LabelImage:     1.4*std + 0.8*mid + 0.5*entropy,
		LabelSchematic: 1.2*hline + 1.2*vline + 0.9*balance + 1.8*signature + 0.35*edge - 0.4*std,
		LabelDiagram:   0.8*edge + 0.8*hline + 0.3*entropy - 0.5*signature,
		LabelTable:     1.3*hline + 1.3*vline + 1.0*balance,
		LabelOther:     0.2,
	}
	if ink < 0.015 {
		scores[LabelOther] += 0.8
	}
	if signature > 0.18 && ink < 0.34 && darkLight < 0.35 {
		scores[LabelSchematic] += 1.2 + signature
		scores[LabelDiagram] *= 0.6
	}
	if hline > 0.45 && vline > 0.35 && signature < 0.10 {
		scores[LabelTable] += 0.9
	}
	if mid > 0.48 && std > 0.45 {
		scores[LabelImage] += 0.8
	}

	bestLabel := LabelOther
	best := -math.MaxFloat64
	var sum float64
	for _, label := range classNames {
		score := math.Max(scores[label], 0.001)
		scores[label] = score
		sum += score
		if score > best {
			best = score
			bestLabel = label
		}
	}
	return bestLabel, best / math.Max(sum, 1e-6)
}

var unsafeLabel = regexp.MustCompile(`[^a-z0-9_-]+`)

func SafeLabel(label string) string {
	out := unsafeLabel.ReplaceAllString(strings.ToLower(label), "_")
	out = strings.Trim(out, "_")
	if out == "" {
		return "block"
	}
	return out
}
