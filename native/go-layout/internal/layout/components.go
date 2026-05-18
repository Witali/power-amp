package layout

func Components(mask []bool, w, h, minArea int) []Box {
	seen := make([]bool, len(mask))
	var boxes []Box
	qx := make([]int, 0, 2048)
	qy := make([]int, 0, 2048)
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			idx := y*w + x
			if seen[idx] || !mask[idx] {
				continue
			}
			seen[idx] = true
			qx = append(qx[:0], x)
			qy = append(qy[:0], y)
			minX, minY, maxX, maxY, area := x, y, x, y, 0
			for head := 0; head < len(qx); head++ {
				cx, cy := qx[head], qy[head]
				area++
				minX, minY = min(minX, cx), min(minY, cy)
				maxX, maxY = max(maxX, cx), max(maxY, cy)
				for _, d := range [][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}} {
					nx, ny := cx+d[0], cy+d[1]
					if nx < 0 || ny < 0 || nx >= w || ny >= h {
						continue
					}
					ni := ny*w + nx
					if seen[ni] || !mask[ni] {
						continue
					}
					seen[ni] = true
					qx = append(qx, nx)
					qy = append(qy, ny)
				}
			}
			if area >= minArea {
				boxes = append(boxes, Box{X: minX, Y: minY, W: maxX - minX + 1, H: maxY - minY + 1})
			}
		}
	}
	return boxes
}

func MergeBoxes(boxes []Box, width, height, margin int) []Box {
	changed := true
	for changed {
		changed = false
		var next []Box
		used := make([]bool, len(boxes))
		for i, box := range boxes {
			if used[i] {
				continue
			}
			merged := box
			used[i] = true
			for j := i + 1; j < len(boxes); j++ {
				if used[j] {
					continue
				}
				if CloseOrOverlap(merged, boxes[j], margin) {
					merged = Union(merged, boxes[j]).Inflate(1, width, height)
					used[j] = true
					changed = true
				}
			}
			next = append(next, merged)
		}
		boxes = next
	}
	return boxes
}

func CloseOrOverlap(a, b Box, margin int) bool {
	return a.X <= b.X2()+margin && a.X2()+margin >= b.X && a.Y <= b.Y2()+margin && a.Y2()+margin >= b.Y
}

func Union(a, b Box) Box {
	x1, y1 := min(a.X, b.X), min(a.Y, b.Y)
	x2, y2 := max(a.X2(), b.X2()), max(a.Y2(), b.Y2())
	return Box{X: x1, Y: y1, W: x2 - x1, H: y2 - y1}
}
