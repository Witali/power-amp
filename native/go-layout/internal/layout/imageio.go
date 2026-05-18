package layout

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/jpeg"
	"image/png"
	"os"
	"path/filepath"
	"strings"
)

func LoadImage(path string) (image.Image, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".jpg", ".jpeg":
		return jpeg.Decode(file)
	case ".png":
		return png.Decode(file)
	default:
		img, _, err := image.Decode(file)
		return img, err
	}
}

func ToRGBA(src image.Image) *image.RGBA {
	b := src.Bounds()
	dst := image.NewRGBA(image.Rect(0, 0, b.Dx(), b.Dy()))
	draw.Draw(dst, dst.Bounds(), src, b.Min, draw.Src)
	return dst
}

func ResizeNearest(src *image.RGBA, maxSide int) (*image.RGBA, float64) {
	w, h := src.Bounds().Dx(), src.Bounds().Dy()
	if maxSide <= 0 || (w <= maxSide && h <= maxSide) {
		return src, 1.0
	}
	scale := float64(maxSide) / float64(max(w, h))
	nw := max(1, int(float64(w)*scale+0.5))
	nh := max(1, int(float64(h)*scale+0.5))
	dst := image.NewRGBA(image.Rect(0, 0, nw, nh))
	for y := 0; y < nh; y++ {
		sy := min(h-1, int(float64(y)/scale))
		for x := 0; x < nw; x++ {
			sx := min(w-1, int(float64(x)/scale))
			dst.SetRGBA(x, y, src.RGBAAt(sx, sy))
		}
	}
	return dst, scale
}

func Gray(src *image.RGBA) []uint8 {
	w, h := src.Bounds().Dx(), src.Bounds().Dy()
	out := make([]uint8, w*h)
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			c := src.RGBAAt(x, y)
			out[y*w+x] = uint8((299*int(c.R) + 587*int(c.G) + 114*int(c.B)) / 1000)
		}
	}
	return out
}

func Crop(src *image.RGBA, box Box) *image.RGBA {
	dst := image.NewRGBA(image.Rect(0, 0, box.W, box.H))
	draw.Draw(dst, dst.Bounds(), src, image.Point{X: box.X, Y: box.Y}, draw.Src)
	return dst
}

func WritePNG(path string, img image.Image) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()
	return png.Encode(file, img)
}

func RGBAColor(r, g, b uint8) color.RGBA {
	return color.RGBA{R: r, G: g, B: b, A: 255}
}

func decodeUnsupported(path string) error {
	return fmt.Errorf("unsupported image format: %s", path)
}
