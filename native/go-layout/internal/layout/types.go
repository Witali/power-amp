package layout

type Options struct {
	MaxAnalysisSide int
	WriteCrops      bool
	OutDir          string
}

type Box struct {
	X int `json:"x"`
	Y int `json:"y"`
	W int `json:"w"`
	H int `json:"h"`
}

func (b Box) X2() int { return b.X + b.W }
func (b Box) Y2() int { return b.Y + b.H }
func (b Box) Area() int {
	if b.W <= 0 || b.H <= 0 {
		return 0
	}
	return b.W * b.H
}

func (b Box) Inflate(pad, width, height int) Box {
	x1 := max(0, b.X-pad)
	y1 := max(0, b.Y-pad)
	x2 := min(width, b.X2()+pad)
	y2 := min(height, b.Y2()+pad)
	return Box{X: x1, Y: y1, W: max(1, x2-x1), H: max(1, y2-y1)}
}

func (b Box) ToList() []int {
	return []int{b.X, b.Y, b.W, b.H}
}

type Block struct {
	Ident      string             `json:"ident"`
	Label      string             `json:"label"`
	Confidence float64            `json:"confidence"`
	BBox       []int              `json:"bbox"`
	CropPath   string             `json:"crop_path,omitempty"`
	Features   map[string]float64 `json:"features"`
}

type Result struct {
	Source        string  `json:"source"`
	Width         int     `json:"width"`
	Height        int     `json:"height"`
	AnalysisScale float64 `json:"analysis_scale"`
	Blocks        []Block `json:"blocks"`
}
