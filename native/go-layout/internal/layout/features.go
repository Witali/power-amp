package layout

import (
	"image"
	"math"
)

func ExtractFeatures(img *image.RGBA, gray []uint8, mask, edges []bool, box Box) map[string]float64 {
	w, h := img.Bounds().Dx(), img.Bounds().Dy()
	area := max(1, box.Area())
	ink, edgeCount := 0, 0
	var sum, sum2 float64
	var hist [16]int
	for y := box.Y; y < box.Y2(); y++ {
		for x := box.X; x < box.X2(); x++ {
			i := y*w + x
			v := float64(gray[i])
			sum += v
			sum2 += v * v
			hist[int(gray[i])/16]++
			if mask[i] {
				ink++
			}
			if edges[i] {
				edgeCount++
			}
		}
	}
	mean := sum / float64(area)
	variance := math.Max(0, sum2/float64(area)-mean*mean)
	hline, vline, balance := LineDensities(mask, box, w)
	signatures := ComponentSignatures(mask, box, w)
	features := map[string]float64{
		"width_ratio":                float64(box.W) / float64(max(1, w)),
		"height_ratio":               float64(box.H) / float64(max(1, h)),
		"area_ratio":                 float64(area) / float64(max(1, w*h)),
		"ink_density":                float64(ink) / float64(area),
		"edge_density":               math.Min(float64(edgeCount)/float64(area)*4.0, 1.0),
		"gray_std":                   math.Min(math.Sqrt(variance)/90.0, 1.0),
		"hline_density":              hline,
		"vline_density":              vline,
		"line_balance":               balance,
		"component_signature_score":  signatures.Score,
		"resistor_symbol_density":    signatures.Resistor,
		"capacitor_symbol_density":   signatures.Capacitor,
		"diode_symbol_density":       signatures.Diode,
		"transistor_symbol_density":  signatures.Transistor,
		"luma_dark_light_ratio":      DarkLightRatio(hist),
		"luma_mid_fraction":          MidFraction(hist, area),
		"luma_hist_entropy":          HistogramEntropy(hist, area),
	}
	return features
}

func LineDensities(mask []bool, box Box, width int) (float64, float64, float64) {
	hitsH, hitsV := 0, 0
	minRunH := max(8, box.W/18)
	minRunV := max(8, box.H/18)
	for y := box.Y; y < box.Y2(); y++ {
		run := 0
		for x := box.X; x < box.X2(); x++ {
			if mask[y*width+x] {
				run++
			} else {
				if run >= minRunH {
					hitsH += run
				}
				run = 0
			}
		}
		if run >= minRunH {
			hitsH += run
		}
	}
	for x := box.X; x < box.X2(); x++ {
		run := 0
		for y := box.Y; y < box.Y2(); y++ {
			if mask[y*width+x] {
				run++
			} else {
				if run >= minRunV {
					hitsV += run
				}
				run = 0
			}
		}
		if run >= minRunV {
			hitsV += run
		}
	}
	area := float64(max(1, box.Area()))
	h := math.Min(float64(hitsH)/area*9.0, 1.0)
	v := math.Min(float64(hitsV)/area*9.0, 1.0)
	return h, v, math.Min(h, v) / math.Max(math.Max(h, v), 1e-6)
}

func HistogramEntropy(hist [16]int, area int) float64 {
	var entropy float64
	for _, count := range hist {
		if count == 0 {
			continue
		}
		p := float64(count) / float64(area)
		entropy -= p * math.Log2(p)
	}
	return entropy / 4.0
}

func DarkLightRatio(hist [16]int) float64 {
	dark := hist[0] + hist[1] + hist[2] + hist[3]
	light := hist[13] + hist[14] + hist[15]
	return float64(dark) / math.Max(float64(light), 1.0)
}

func MidFraction(hist [16]int, area int) float64 {
	mid := 0
	for i := 4; i <= 12; i++ {
		mid += hist[i]
	}
	return float64(mid) / float64(max(1, area))
}
