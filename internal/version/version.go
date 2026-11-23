// Package version reads and compares launcher versions. It is separate from the
// main package, whose init needs a portapp.json and cannot run in tests.
package version

import (
	"strconv"
	"strings"
)

// FromProperties returns app.version from the content of build.properties, or
// an empty string when it is missing.
func FromProperties(text string) string {
	for _, line := range strings.Split(text, "\n") {
		key, value, _ := strings.Cut(line, "=")
		if strings.TrimSpace(key) == "app.version" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

// Newer reports whether dotted version a is greater than b.
func Newer(a, b string) bool {
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
