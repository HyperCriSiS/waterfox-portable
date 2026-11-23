package version

import (
	"os"
	"regexp"
	"testing"
)

func TestFromProperties(t *testing.T) {
	for text, want := range map[string]string{
		"app.version = 1.0.3\napp.release = 4\n":      "1.0.3",
		"app = x\r\napp.version = 1.0.3\r\n":          "1.0.3",
		"waterfox.version = 6.7.8\napp.version=2.0.0": "2.0.0",
		"waterfox.version = 6.7.8\n":                  "",
	} {
		if got := FromProperties(text); got != want {
			t.Errorf("FromProperties(%q) = %q, want %q", text, got, want)
		}
	}
}

// The launcher embeds this file. An unreadable version would silently turn the
// update notice off.
func TestFromPropertiesReadsRealFile(t *testing.T) {
	text, err := os.ReadFile("../../build.properties")
	if err != nil {
		t.Fatal(err)
	}
	if got := FromProperties(string(text)); !regexp.MustCompile(`^\d+\.\d+\.\d+$`).MatchString(got) {
		t.Fatalf("unexpected launcher version %q", got)
	}
}

func TestNewer(t *testing.T) {
	for _, c := range []struct {
		a, b string
		want bool
	}{
		{"1.0.3", "1.0.2", true},
		{"1.0.2", "1.0.3", false},
		{"1.0.3", "1.0.3", false},
		{"1.0.10", "1.0.9", true},
		{"1.1", "1.0.9", true},
		{"1.0", "1.0.0", false},
		{"", "1.0.0", false},
		{"v1.0.4", "1.0.3", false},
	} {
		if got := Newer(c.a, c.b); got != c.want {
			t.Errorf("Newer(%q, %q) = %v, want %v", c.a, c.b, got, c.want)
		}
	}
}
