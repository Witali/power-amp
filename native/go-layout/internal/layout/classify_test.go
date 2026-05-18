package layout

import "testing"

func TestClassifyPrefersSchematicForComponentSignatures(t *testing.T) {
	label, confidence := Classify(map[string]float64{
		"ink_density":               0.12,
		"edge_density":              0.30,
		"gray_std":                  0.18,
		"hline_density":             0.20,
		"vline_density":             0.18,
		"line_balance":              0.24,
		"component_signature_score": 0.36,
		"luma_dark_light_ratio":     0.10,
		"luma_mid_fraction":         0.12,
		"luma_hist_entropy":         0.38,
	})
	if label != LabelSchematic {
		t.Fatalf("label = %q, want %q", label, LabelSchematic)
	}
	if confidence <= 0 {
		t.Fatalf("confidence = %f, want positive value", confidence)
	}
}

func TestSafeLabelKeepsSchematicSimple(t *testing.T) {
	if got := SafeLabel(LabelSchematic); got != "schematic" {
		t.Fatalf("SafeLabel(%q) = %q, want schematic", LabelSchematic, got)
	}
}
