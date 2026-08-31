//go:generate go install -v github.com/josephspurrier/goversioninfo/cmd/goversioninfo
//go:generate goversioninfo -icon=res/papp.ico -manifest=res/papp.manifest

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"text/template"

	"github.com/Jeffail/gabs/v2"
	"github.com/pkg/errors"
	"github.com/portapps/portapps"
	"github.com/portapps/portapps/pkg/files"
	"github.com/portapps/portapps/pkg/mutex"
	"github.com/portapps/portapps/pkg/registry"
	"github.com/portapps/portapps/pkg/shortcut"
	"github.com/portapps/portapps/pkg/win"
	"github.com/rs/zerolog/log"
)

var (
	// App
	app *portapps.App
	// Config
	cfg *config
)

type config struct {
	Cleanup           bool `yaml:"cleanup"`
	MultipleInstances bool `yaml:"multiple_instances"`
}

func init() {
	var err error
	app, err = portapps.New("waterfox-portable", "Waterfox")
	if err != nil {
		log.Fatal().Err(err).Msg("Cannot initialize application")
	}

	cfg = &config{
		Cleanup:           true,
		MultipleInstances: false,
	}
	if err := app.ParseConfig(cfg); err != nil {
		log.Fatal().Err(err).Msg("Cannot load configuration")
	}
}

func main() {
	defer app.Close()

	profileFolder := filepath.Join(app.DataPath, "profile", "default")
	if err := os.MkdirAll(profileFolder, os.ModePerm); err != nil {
		log.Fatal().Err(err).Msg("Cannot create profile directory.")
	}

	app.Process = filepath.Join(app.AppPath, "waterfox.exe")
	app.Args = []string{
		"--profile",
		profileFolder,
	}

	// Set env vars
	crashreporterFolder := filepath.Join(app.DataPath, "crashreporter")
	if err := os.MkdirAll(crashreporterFolder, os.ModePerm); err != nil {
		log.Fatal().Err(err).Msg("Cannot create crash reporter directory.")
	}
	pluginsFolder := filepath.Join(app.DataPath, "plugins")
	if err := os.MkdirAll(pluginsFolder, os.ModePerm); err != nil {
		log.Fatal().Err(err).Msg("Cannot create plugins directory.")
	}
	os.Setenv("MOZ_CRASHREPORTER", "0")
	os.Setenv("MOZ_CRASHREPORTER_DATA_DIRECTORY", crashreporterFolder)
	os.Setenv("MOZ_CRASHREPORTER_DISABLE", "1")
	os.Setenv("MOZ_CRASHREPORTER_NO_REPORT", "1")
	os.Setenv("MOZ_DATA_REPORTING", "0")
	os.Setenv("MOZ_MAINTENANCE_SERVICE", "0")
	os.Setenv("MOZ_PLUGIN_PATH", pluginsFolder)

	// Create and check mutex
	mu, err := mutex.Create(app.ID)
	defer mutex.Release(mu)
	if err != nil {
		if !cfg.MultipleInstances {
			log.Error().Msg("You have to enable multiple instances in your configuration if you want to launch another instance")
			if _, err = win.MsgBox(
				fmt.Sprintf("%s portable", app.Name),
				"Other instance detected. You have to enable multiple instances in your configuration if you want to launch another instance.",
				win.MsgBoxBtnOk|win.MsgBoxIconError); err != nil {
				log.Error().Err(err).Msg("Cannot create dialog box")
			}
			return
		} else {
			log.Warn().Msg("Another instance is already running")
		}
	}

	// Cleanup on exit
	if cfg.Cleanup {
		defer func() {
			regKey := registry.Key{
				Key:  `HKCU\SOFTWARE\Waterfox Ltd.`,
				Arch: "32",
			}
			if regKey.Exists() {
				if err := regKey.Delete(true); err != nil {
					log.Error().Err(err).Msg("Cannot remove registry key")
				}
			}
			files.Cleanup(
				filepath.Join(os.Getenv("APPDATA"), "Waterfox"),
				filepath.Join(os.Getenv("LOCALAPPDATA"), "Waterfox"),
			)
		}()
	}

	// Multiple instances
	if cfg.MultipleInstances {
		log.Info().Msg("Multiple instances enabled")
		app.Args = append(app.Args, "--no-remote")
	}

	// Policies
	if err := createPolicies(); err != nil {
		log.Fatal().Err(err).Msg("Cannot create policies")
	}

	// Autoconfig
	prefFolder := filepath.Join(app.AppPath, "defaults", "pref")
	if err := os.MkdirAll(prefFolder, os.ModePerm); err != nil {
		log.Fatal().Err(err).Msg("Cannot create preferences directory.")
	}
	autoconfig := filepath.Join(prefFolder, "autoconfig.js")
	if err := os.WriteFile(autoconfig, []byte(`//
pref("general.config.filename", "portapps.cfg");
pref("general.config.obscure_value", 0);`), 0644); err != nil {
		log.Fatal().Err(err).Msg("Cannot write autoconfig.js")
	}

	// Mozilla cfg
	mozillaCfgPath := filepath.Join(app.AppPath, "portapps.cfg")
	mozillaCfgFile, err := os.Create(mozillaCfgPath)
	if err != nil {
		log.Fatal().Err(err).Msg("Cannot create portapps.cfg")
	}
	mozillaCfgTpl := template.Must(template.New("mozillaCfg").Parse(`// Extensions scopes
lockPref("extensions.enabledScopes", 4);
lockPref("extensions.autoDisableScopes", 3);

// Don't show 'know your rights' on first run
pref("browser.rights.3.shown", true);

// Don't show WhatsNew on first run after every update
pref("browser.startup.homepage_override.mstone", "ignore");
`))
	if err := mozillaCfgTpl.Execute(mozillaCfgFile, ""); err != nil {
		log.Fatal().Err(err).Msg("Cannot write portapps.cfg")
	}

	// Fix extensions path
	if err := updateAddonStartup(profileFolder); err != nil {
		log.Error().Err(err).Msg("Cannot fix extensions path")
	}

	// Copy default shortcut
	shortcutPath := filepath.Join(files.StartMenuPath(), "Waterfox Portable.lnk")
	defaultShortcut, err := assets.Asset("Waterfox.lnk")
	if err != nil {
		log.Error().Err(err).Msg("Cannot load asset Waterfox.lnk")
	}
	err = os.WriteFile(shortcutPath, defaultShortcut, 0644)
	if err != nil {
		log.Error().Err(err).Msg("Cannot write default shortcut")
	}

	// Update default shortcut
	err = shortcut.Create(shortcut.Shortcut{
		ShortcutPath:     shortcutPath,
		TargetPath:       app.Process,
		Arguments:        shortcut.Property{Clear: true},
		Description:      shortcut.Property{Value: "Waterfox Portable by Portapps"},
		IconLocation:     shortcut.Property{Value: app.Process},
		WorkingDirectory: shortcut.Property{Value: app.AppPath},
	})
	if err != nil {
		log.Error().Err(err).Msg("Cannot create shortcut")
	}
	defer func() {
		if err := os.Remove(shortcutPath); err != nil {
			log.Error().Err(err).Msg("Cannot remove shortcut")
		}
	}()

	defer app.Close()
	app.Launch(os.Args[1:])
}

func createPolicies() error {
	distributionFolder := filepath.Join(app.AppPath, "distribution")
	if err := os.MkdirAll(distributionFolder, os.ModePerm); err != nil {
		return errors.Wrap(err, "Cannot create distribution folder")
	}
	appFile := filepath.Join(distributionFolder, "policies.json")
	dataFile := filepath.Join(app.DataPath, "policies.json")
	defaultPolicies := struct {
		Policies map[string]interface{} `json:"policies"`
	}{
		Policies: map[string]interface{}{
			"DontCheckDefaultBrowser": true,
		},
	}

	jsonPolicies, err := gabs.Consume(defaultPolicies)
	if err != nil {
		return errors.Wrap(err, "Cannot consume default policies")
	}
	log.Debug().Msgf("Default policies: %s", jsonPolicies.String())

	if _, err := os.Stat(dataFile); err == nil {
		rawCustomPolicies, err := os.ReadFile(dataFile)
		if err != nil {
			return errors.Wrap(err, "Cannot read custom policies")
		}

		jsonPolicies, err = gabs.ParseJSON(rawCustomPolicies)
		if err != nil {
			return errors.Wrap(err, "Cannot consume custom policies")
		}
		log.Debug().Msgf("Custom policies: %s", jsonPolicies.String())

		jsonPolicies.Set(true, "policies", "DontCheckDefaultBrowser")
	}

	log.Debug().Msgf("Applied policies: %s", jsonPolicies.String())
	err = os.WriteFile(appFile, []byte(jsonPolicies.StringIndent("", "  ")), 0644)
	if err != nil {
		return errors.Wrap(err, "Cannot write policies")
	}

	return nil
}

func updateAddonStartup(profileFolder string) error {
	lz4File := filepath.Join(profileFolder, "addonStartup.json.lz4")
	if _, err := os.Stat(lz4File); os.IsNotExist(err) || app.Prev.RootPath == "" {
		return nil
	}

	lz4Raw, err := mozLz4Decompress(lz4File)
	if err != nil {
		return err
	}

	var addonStartup map[string]interface{}
	if err := json.Unmarshal(lz4Raw, &addonStartup); err != nil {
		return errors.Wrap(err, "Cannot unmarshal addonStartup")
	}

	locations, ok := addonStartup["locations"].(map[string]interface{})
	if !ok {
		return nil
	}

	for _, locationRaw := range locations {
		location, ok := locationRaw.(map[string]interface{})
		if !ok {
			continue
		}
		addons, ok := location["addons"].(map[string]interface{})
		if !ok {
			continue
		}
		for _, addonRaw := range addons {
			addon, ok := addonRaw.(map[string]interface{})
			if !ok {
				continue
			}
		path, ok := addon["path"].(string)
			if !ok {
				continue
			}
		if strings.Contains(path, app.Prev.RootPath) {
				addon["path"] = strings.Replace(path, app.Prev.RootPath, app.RootPath, 1)
			}
		}
	}

	updatedRaw, err := json.Marshal(addonStartup)
	if err != nil {
		return errors.Wrap(err, "Cannot marshal addonStartup")
	}

	if err := mozLz4Compress(lz4File, updatedRaw); err != nil {
		return err
	}
	return nil
}
