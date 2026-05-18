package layout

import (
	"fmt"
	"path/filepath"
	"sort"
)

const (
	LabelText      = "text"
	LabelImage     = "image"
	LabelSchematic = "schematic"
	LabelDiagram   = "diagram"
	LabelTable     = "table"
	LabelOther     = "other"
)

var classNames = []string{LabelText, LabelImage, LabelSchematic, LabelDiagram, LabelTable, LabelOther}

func ScanFile(path string, opts Options) (Result, error) {
	if opts.MaxAnalysisSide == 0 {
		opts.MaxAnalysisSide = 1800
	}
	src, err := LoadImage(path)
	if err != nil {
		return Result{}, err
	}
	original := ToRGBA(src)
	analysis, scale := ResizeNearest(original, opts.MaxAnalysisSide)
	w, h := analysis.Bounds().Dx(), analysis.Bounds().Dy()
	gray := Gray(analysis)
	threshold := Otsu(gray)
	mask := ForegroundMask(gray, threshold)
	edges := SimpleEdges(gray, w, h)

	boxes := Components(mask, w, h, max(24, (w*h)/25000))
	boxes = MergeBoxes(boxes, w, h, max(5, min(w, h)/180))
	sort.Slice(boxes, func(i, j int) bool {
		if boxes[i].Y == boxes[j].Y {
			return boxes[i].X < boxes[j].X
		}
		return boxes[i].Y < boxes[j].Y
	})

	result := Result{
		Source:        path,
		Width:         original.Bounds().Dx(),
		Height:        original.Bounds().Dy(),
		AnalysisScale: scale,
	}

	for i, box := range boxes {
		features := ExtractFeatures(analysis, gray, mask, edges, box)
		label, confidence := Classify(features)
		origBox := Box{
			X: int(float64(box.X)/scale + 0.5),
			Y: int(float64(box.Y)/scale + 0.5),
			W: int(float64(box.W)/scale + 0.5),
			H: int(float64(box.H)/scale + 0.5),
		}
		block := Block{
			Ident:      fmt.Sprintf("%03d_%s", i+1, SafeLabel(label)),
			Label:      label,
			Confidence: confidence,
			BBox:       origBox.ToList(),
			Features:   features,
		}
		if opts.WriteCrops && opts.OutDir != "" {
			cropName := filepath.Join("blocks", SafeLabel(label), block.Ident+".png")
			cropPath := filepath.Join(opts.OutDir, cropName)
			if err := WritePNG(cropPath, Crop(original, origBox)); err == nil {
				block.CropPath = filepath.ToSlash(cropName)
			}
		}
		result.Blocks = append(result.Blocks, block)
	}
	return result, nil
}
