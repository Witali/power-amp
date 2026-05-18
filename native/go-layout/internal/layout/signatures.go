package layout

import "math"

type SignatureFeatures struct {
	Score      float64
	Resistor   float64
	Capacitor  float64
	Diode      float64
	Transistor float64
}

func ComponentSignatures(mask []bool, box Box, width int) SignatureFeatures {
	components := ComponentsInBox(mask, box, width, 4)
	resistors, circles := 0, 0
	for _, c := range components {
		if c.W < 5 || c.H < 5 {
			continue
		}
		aspect := float64(max(c.W, c.H)) / float64(max(1, min(c.W, c.H)))
		fill := float64(c.Area()) / float64(max(1, c.W*c.H))
		if aspect >= 1.25 && aspect <= 8.0 && fill <= 0.95 {
			resistors++
		}
		if aspect <= 1.45 && fill >= 0.08 && fill <= 0.72 {
			circles++
		}
	}
	caps := CountParallelPlates(mask, box, width)
	diodes := CountTriangleLike(mask, box, width)
	normalizer := math.Max(1.0, float64(box.Area())/42000.0)
	res := math.Min(float64(resistors)/normalizer, 1.0)
	cap := math.Min(float64(caps)/normalizer, 1.0)
	dio := math.Min(float64(diodes)/normalizer, 1.0)
	tr := math.Min(float64(circles)/normalizer, 1.0)
	return SignatureFeatures{
		Score:      math.Min(0.34*res+0.30*cap+0.22*dio+0.18*tr, 1.0),
		Resistor:   res,
		Capacitor:  cap,
		Diode:      dio,
		Transistor: tr,
	}
}

func ComponentsInBox(mask []bool, box Box, width, minArea int) []Box {
	sub := make([]bool, box.W*box.H)
	for y := 0; y < box.H; y++ {
		for x := 0; x < box.W; x++ {
			sub[y*box.W+x] = mask[(box.Y+y)*width+box.X+x]
		}
	}
	boxes := Components(sub, box.W, box.H, minArea)
	for i := range boxes {
		boxes[i].X += box.X
		boxes[i].Y += box.Y
	}
	return boxes
}

func CountParallelPlates(mask []bool, box Box, width int) int {
	count := 0
	maxGap := max(4, min(box.W, box.H)/18)
	for y := box.Y; y < box.Y2(); y++ {
		for x := box.X; x < box.X2()-maxGap; x++ {
			if !verticalRun(mask, width, x, y, 8) {
				continue
			}
			for gap := 2; gap <= maxGap; gap++ {
				if verticalRun(mask, width, x+gap, y, 8) {
					count++
					x += gap + 2
					break
				}
			}
		}
	}
	return count
}

func verticalRun(mask []bool, width, x, y, minLen int) bool {
	run := 0
	height := len(mask) / width
	for yy := y; yy < height && yy < y+minLen+4; yy++ {
		if mask[yy*width+x] {
			run++
		}
	}
	return run >= minLen
}

func CountTriangleLike(mask []bool, box Box, width int) int {
	count := 0
	for _, c := range ComponentsInBox(mask, box, width, 8) {
		if c.W < 8 || c.H < 8 || c.W > box.W/3 || c.H > box.H/3 {
			continue
		}
		aspect := float64(max(c.W, c.H)) / float64(max(1, min(c.W, c.H)))
		if aspect > 2.8 {
			continue
		}
		left, right := 0, 0
		for y := c.Y; y < c.Y2(); y++ {
			for x := c.X; x < c.X2(); x++ {
				if !mask[y*width+x] {
					continue
				}
				if x < c.X+c.W/2 {
					left++
				} else {
					right++
				}
			}
		}
		if left > 0 && right > 0 && math.Min(float64(left), float64(right))/math.Max(float64(left), float64(right)) > 0.25 {
			count++
		}
	}
	return count
}
