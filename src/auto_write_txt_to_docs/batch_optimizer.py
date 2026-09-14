class BatchDeduplicationOptimizer:
    def __init__(self, threshold=0.95, max_interval=60.0):
        self.threshold = threshold
        self.max_interval = max_interval
        self.current_interval = 0.5
        self.batch_results = []

    def record_result(self, total_lines, duplicate_lines):
        self.batch_results.append((total_lines, duplicate_lines))
        if len(self.batch_results) > 10:
            self.batch_results.pop(0)

    def should_increase_interval(self):
        if not self.batch_results:
            return False
        total = sum(t for t, _ in self.batch_results)
        dups = sum(d for _, d in self.batch_results)
        if total == 0:
            return False
        return (dups / total) >= self.threshold

    def get_next_interval(self):
        if self.should_increase_interval():
            self.current_interval = min(self.current_interval * 2, self.max_interval)
        else:
            self.current_interval = max(0.5, self.current_interval / 2)
        return self.current_interval
