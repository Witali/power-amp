package layout

func Otsu(gray []uint8) uint8 {
	var hist [256]int
	for _, v := range gray {
		hist[v]++
	}
	total := len(gray)
	sum := 0
	for i, c := range hist {
		sum += i * c
	}
	sumB, wB := 0, 0
	bestVar := -1.0
	best := 128
	for t := 0; t < 256; t++ {
		wB += hist[t]
		if wB == 0 {
			continue
		}
		wF := total - wB
		if wF == 0 {
			break
		}
		sumB += t * hist[t]
		mB := float64(sumB) / float64(wB)
		mF := float64(sum-sumB) / float64(wF)
		between := float64(wB) * float64(wF) * (mB - mF) * (mB - mF)
		if between > bestVar {
			bestVar = between
			best = t
		}
	}
	return uint8(best)
}

func ForegroundMask(gray []uint8, threshold uint8) []bool {
	mask := make([]bool, len(gray))
	limit := int(threshold) - 6
	for i, v := range gray {
		mask[i] = int(v) <= limit
	}
	return mask
}

func SimpleEdges(gray []uint8, w, h int) []bool {
	edges := make([]bool, w*h)
	for y := 1; y < h-1; y++ {
		for x := 1; x < w-1; x++ {
			i := y*w + x
			gx := int(gray[i+1]) - int(gray[i-1])
			gy := int(gray[i+w]) - int(gray[i-w])
			if abs(gx)+abs(gy) > 44 {
				edges[i] = true
			}
		}
	}
	return edges
}
