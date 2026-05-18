package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"poweramp/native/go-layout/internal/layout"
)

func main() {
	imagePath := flag.String("image", "", "input JPEG/PNG page image")
	outDir := flag.String("out", "layout-out", "output directory")
	maxSide := flag.Int("max-side", 1800, "maximum analysis image side")
	writeCrops := flag.Bool("crops", false, "write cropped block PNG files")
	flag.Parse()

	if *imagePath == "" {
		fmt.Fprintln(os.Stderr, "--image is required")
		os.Exit(2)
	}

	result, err := layout.ScanFile(*imagePath, layout.Options{
		MaxAnalysisSide: *maxSide,
		WriteCrops:      *writeCrops,
		OutDir:          *outDir,
	})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	if err := os.MkdirAll(*outDir, 0o755); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	jsonPath := filepath.Join(*outDir, "layout.json")
	if err := os.WriteFile(jsonPath, append(data, '\n'), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(jsonPath)
}
