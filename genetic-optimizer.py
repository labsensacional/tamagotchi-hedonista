
import os
import random
import multiprocessing as mp

from simulation import Simulation

# =============================================================================
# OPTIMIZER - Parallel Genetic Algorithm with Local Search
# =============================================================================

# Global variable for worker processes (each process gets its own Simulation)
_worker_sim = None
_worker_event_names = None


def _init_worker():
    """Initialize a Simulation instance in each worker process."""
    global _worker_sim, _worker_event_names
    _worker_sim = Simulation()
    _worker_event_names = _worker_sim.get_event_names()


def _evaluate_fitness(sequence: list[str]) -> float:
    """Worker function to evaluate fitness (called in parallel)."""
    global _worker_sim
    result = _worker_sim.run(sequence, max_hours=10.0)
    if not result['viable']:
        return 0.0
    return result['total_pleasure']


def _local_search_worker(args: tuple) -> tuple[list[str], float]:
    """
    Worker function for parallel local search.
    args: (sequence, steps)
    Returns: (improved_sequence, fitness)
    """
    global _worker_sim, _worker_event_names
    sequence, steps = args

    current = list(sequence)
    result = _worker_sim.run(current, max_hours=10.0)
    current_fitness = result['total_pleasure'] if result['viable'] else 0.0

    for _ in range(steps):
        # Try changing one random position
        pos = random.randint(0, len(current) - 1)
        new_event = random.choice(_worker_event_names)

        candidate = current.copy()
        candidate[pos] = new_event
        result = _worker_sim.run(candidate, max_hours=10.0)
        candidate_fitness = result['total_pleasure'] if result['viable'] else 0.0

        # Also try swapping two positions
        if random.random() < 0.3:
            pos2 = random.randint(0, len(current) - 1)
            candidate2 = current.copy()
            candidate2[pos], candidate2[pos2] = candidate2[pos2], candidate2[pos]
            result2 = _worker_sim.run(candidate2, max_hours=10.0)
            fitness2 = result2['total_pleasure'] if result2['viable'] else 0.0
            if fitness2 > candidate_fitness:
                candidate = candidate2
                candidate_fitness = fitness2

        # Keep if better
        if candidate_fitness > current_fitness:
            current = candidate
            current_fitness = candidate_fitness

    return (current, current_fitness)


class GeneticOptimizer:
    """
    Memetic algorithm: Genetic algorithm + local search for better convergence.

    Improvements over basic GA:
    - Adaptive mutation rate (high early, low late)
    - Two-point crossover for better gene mixing
    - Local search (hill climbing) on elite solutions
    - Early stopping when stuck
    """

    def __init__(
        self,
        simulation: Simulation,
        population_size: int = 500,
        sequence_length: int = 40,
        generations: int = 1000,
        mutation_rate: float = 0.15,
        elite_fraction: float = 0.1,
        local_search_steps: int = 5,
        early_stop_generations: int = 200,
        n_workers: int = None  # None = use all CPUs
    ):
        self.sim = simulation
        self.pop_size = population_size
        self.seq_length = sequence_length
        self.generations = generations
        self.base_mutation_rate = mutation_rate
        self.elite_count = max(2, int(population_size * elite_fraction))
        self.event_names = simulation.get_event_names()
        self.local_search_steps = local_search_steps
        self.early_stop_gens = early_stop_generations

        # Number of parallel workers
        self.n_workers = n_workers or os.cpu_count()

        # Cache for fitness evaluations (used in single-threaded parts)
        self._fitness_cache = {}

    def random_sequence(self) -> list[str]:
        """Generate a random event sequence."""
        return [random.choice(self.event_names) for _ in range(self.seq_length)]

    def fitness(self, sequence: list[str]) -> float:
        """Evaluate fitness of a sequence (with caching)."""
        key = tuple(sequence)
        if key not in self._fitness_cache:
            result = self.sim.run(sequence, max_hours=10.0)
            if not result['viable']:
                self._fitness_cache[key] = 0.0
            else:
                self._fitness_cache[key] = result['total_pleasure']
        return self._fitness_cache[key]

    def two_point_crossover(self, parent1: list[str], parent2: list[str]) -> list[str]:
        """Two-point crossover for better gene mixing."""
        length = len(parent1)
        p1, p2 = sorted(random.sample(range(1, length), 2))
        return parent1[:p1] + parent2[p1:p2] + parent1[p2:]

    def mutate(self, sequence: list[str], rate: float) -> list[str]:
        """Randomly mutate some events."""
        result = sequence.copy()
        for i in range(len(result)):
            if random.random() < rate:
                result[i] = random.choice(self.event_names)
        return result

    def local_search(self, sequence: list[str], steps: int) -> tuple[list[str], float]:
        """
        Hill climbing: try small changes to improve the sequence.
        Returns improved sequence and its fitness.
        """
        current = sequence.copy()
        current_fitness = self.fitness(current)

        for _ in range(steps):
            # Try changing one random position
            pos = random.randint(0, len(current) - 1)
            new_event = random.choice(self.event_names)

            candidate = current.copy()
            candidate[pos] = new_event
            candidate_fitness = self.fitness(candidate)

            # Also try swapping two positions
            if random.random() < 0.3:
                pos2 = random.randint(0, len(current) - 1)
                candidate2 = current.copy()
                candidate2[pos], candidate2[pos2] = candidate2[pos2], candidate2[pos]
                fitness2 = self.fitness(candidate2)
                if fitness2 > candidate_fitness:
                    candidate = candidate2
                    candidate_fitness = fitness2

            # Keep if better
            if candidate_fitness > current_fitness:
                current = candidate
                current_fitness = candidate_fitness

        return current, current_fitness

    def get_adaptive_mutation_rate(self, generation: int) -> float:
        """
        Adaptive mutation: high early (exploration), low late (exploitation).
        """
        progress = generation / max(1, self.generations - 1)
        # Start at 2x base rate, end at 0.3x base rate
        multiplier = 2.0 - 1.7 * progress
        return self.base_mutation_rate * multiplier

    def optimize(self, verbose: bool = True) -> dict:
        """
        Run genetic optimization with local search (parallelized).
        """
        # Initialize population
        population = [self.random_sequence() for _ in range(self.pop_size)]
        history = []
        best_ever = None
        best_fitness_ever = 0
        generations_without_improvement = 0

        if verbose:
            print(f"Starting optimization with {self.n_workers} CPU workers...")

        # Create process pool
        with mp.Pool(processes=self.n_workers, initializer=_init_worker) as pool:

            for gen in range(self.generations):
                # Adaptive mutation rate
                mutation_rate = self.get_adaptive_mutation_rate(gen)

                # Evaluate fitness IN PARALLEL
                fitnesses = pool.map(_evaluate_fitness, population)
                scored = list(zip(population, fitnesses))
                scored.sort(key=lambda x: x[1], reverse=True)

                best_fitness = scored[0][1]
                history.append(best_fitness)

                # Track improvement
                if best_fitness > best_fitness_ever:
                    best_fitness_ever = best_fitness
                    best_ever = scored[0][0].copy()
                    generations_without_improvement = 0
                else:
                    generations_without_improvement += 1

                if verbose and gen % 10 == 0:
                    print(f"Gen {gen}: best={best_fitness:.2f}, "
                          f"all-time={best_fitness_ever:.2f}, "
                          f"stagnant={generations_without_improvement}, "
                          f"mut_rate={mutation_rate:.3f}")

                # Early stopping
                if generations_without_improvement >= self.early_stop_gens:
                    if verbose:
                        print(f"Early stopping at gen {gen} "
                              f"(no improvement for {generations_without_improvement} gens, "
                              f"threshold={self.early_stop_gens})")
                    break

                # Local search on elite solutions IN PARALLEL
                elite_seqs = [seq for seq, _ in scored[:self.elite_count]]
                # Prepare args: (sequence, steps) for each elite
                local_search_args = [(seq, self.local_search_steps) for seq in elite_seqs]

                # Run local search in parallel
                improved_results = pool.map(_local_search_worker, local_search_args)

                elite = []
                for improved_seq, improved_fit in improved_results:
                    elite.append(improved_seq)
                    if improved_fit > best_fitness_ever:
                        best_fitness_ever = improved_fit
                        best_ever = list(improved_seq)
                        generations_without_improvement = 0  # Reset on local search improvement too!

                # Create next generation
                next_gen = elite.copy()

                while len(next_gen) < self.pop_size:
                    # Tournament selection (size 3 for more pressure)
                    tournament_size = min(3, len(scored) // 2)
                    candidates = random.sample(scored[:len(scored)//2], tournament_size)
                    parent1 = max(candidates, key=lambda x: x[1])[0]
                    candidates = random.sample(scored[:len(scored)//2], tournament_size)
                    parent2 = max(candidates, key=lambda x: x[1])[0]

                    # Two-point crossover
                    child = self.two_point_crossover(parent1, parent2)
                    child = self.mutate(child, mutation_rate)
                    next_gen.append(child)

                population = next_gen

        # Final local search on best solution
        if best_ever:
            best_ever, best_fitness_ever = self.local_search(
                best_ever, self.local_search_steps * 3
            )

        return {
            'best_sequence': best_ever,
            'best_fitness': best_fitness_ever,
            'history': history,
            'generations_run': len(history)
        }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("HEDONISTIC TAMAGOTCHI - MVP")
    print("=" * 60)

    # Create simulation
    sim = Simulation(time_step=0.1)

    print("\nAvailable events:", sim.get_event_names())

    # Test a manual sequence first
    print("\n" + "-" * 60)
    print("Testing manual sequence...")
    print("-" * 60)

    manual_sequence = [
        'eat', 'deep_breathing', 'cuddling',
        'light_stimulation', 'light_stimulation', 'edging',
        'edging', 'light_pain', 'edging', 'orgasm',
        'cuddling', 'rest'
    ]

    result = sim.run(manual_sequence, verbose=True)
    print(f"\nManual sequence result:")
    print(f"  Total pleasure: {result['total_pleasure']:.2f}")
    print(f"  Avg pleasure: {result['avg_pleasure']:.2f}")
    print(f"  Viable: {result['viable']}")

    # Run genetic optimizer
    print("\n" + "-" * 60)
    print("Running genetic optimizer (this may take a moment)...")
    print("-" * 60)

    optimizer = GeneticOptimizer(
        simulation=sim,
        population_size=1000,
        sequence_length=120,  # longer sequence to cover full 10h even with skipped events
        generations=1000,
        mutation_rate=0.15
    )

    opt_result = optimizer.optimize(verbose=True)

    print(f"\nOptimization complete!")
    print(f"Best fitness: {opt_result['best_fitness']:.2f}")
    print(f"\nBest sequence found:")

    # Show the sequence in a readable way
    seq = opt_result['best_sequence']
    # Compress consecutive same events
    compressed = []
    i = 0
    while i < len(seq):
        event = seq[i]
        count = 1
        while i + count < len(seq) and seq[i + count] == event:
            count += 1
        if count > 1:
            compressed.append(f"{event} x{count}")
        else:
            compressed.append(event)
        i += count

    print(" -> ".join(compressed[:20]))  # Show first 20 groups
    if len(compressed) > 20:
        print(f"   ... and {len(compressed) - 20} more")

    # Run the best sequence with verbose output
    print("\n" + "-" * 60)
    print("Running best sequence in detail...")
    print("-" * 60)

    best_result = sim.run(opt_result['best_sequence'], verbose=True)
    print(f"\nFinal state: {best_result['final_state']}")


if __name__ == "__main__":
    main()
