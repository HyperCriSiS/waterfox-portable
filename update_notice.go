package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/portapps/portapps/v3/pkg/log"
	"github.com/portapps/portapps/v3/pkg/win"
)

// notifyLauncherUpdate tells the user once per version when a release with a
// newer launcher exists. Waterfox updates itself, so a release that only
// raises app.release is ignored.
func notifyLauncherUpdate() {
	for _, arg := range os.Args[1:] {
		if arg == "--headless" {
			return
		}
	}
	repo := strings.TrimPrefix(app.Info.URL, "https://github.com/")
	client := http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get("https://api.github.com/repos/" + repo + "/releases/latest")
	if err != nil {
		log.Debug().Err(err).Msg("Cannot check for launcher updates")
		return
	}
	defer resp.Body.Close()
	var release struct {
		TagName string `json:"tag_name"`
		HTMLURL string `json:"html_url"`
	}
	if resp.StatusCode != http.StatusOK || json.NewDecoder(resp.Body).Decode(&release) != nil {
		return
	}

	latest, _, _ := strings.Cut(release.TagName, "-")
	if !newerVersion(latest, app.Info.Version) {
		return
	}
	seenFile := filepath.Join(app.DataPath, "launcher-update-seen.txt")
	if seen, _ := os.ReadFile(seenFile); strings.TrimSpace(string(seen)) == latest {
		return
	}
	if err := os.WriteFile(seenFile, []byte(latest), 0644); err != nil {
		log.Error().Err(err).Msg("Cannot remember launcher update notice")
	}

	answer, err := win.MsgBox(
		fmt.Sprintf("%s portable", app.Name),
		fmt.Sprintf("A new portable launcher is available (%s, you have %s). Waterfox itself keeps updating on its own; this update is for the portable launcher.\n\nOpen the download page?", latest, app.Info.Version),
		win.MsgBoxBtnYesNo|win.MsgBoxIconInformation)
	if err != nil {
		log.Error().Err(err).Msg("Cannot create dialog box")
		return
	}
	if answer == win.MsgBoxSelectYes && strings.HasPrefix(release.HTMLURL, "https://github.com/") {
		_ = exec.Command("rundll32", "url.dll,FileProtocolHandler", release.HTMLURL).Start()
	}
}

// newerVersion reports whether dotted version a is greater than b.
func newerVersion(a, b string) bool {
	as, bs := strings.Split(a, "."), strings.Split(b, ".")
	for i := 0; i < len(as) || i < len(bs); i++ {
		var x, y int
		if i < len(as) {
			x, _ = strconv.Atoi(as[i])
		}
		if i < len(bs) {
			y, _ = strconv.Atoi(bs[i])
		}
		if x != y {
			return x > y
		}
	}
	return false
}
