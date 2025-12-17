# Simulation Pipeline Examples

This document describes the three simulation pipeline examples provided in the `examples/` directory. Each example demonstrates the daily/hourly simulation pattern with different approaches to agent behavior.

## Overview

All three examples follow the same simulation structure:
- **Daily loop**: Iterate through simulation days
- **Hourly loop**: Process time slots within each day
- **Agent sampling**: Select active agents based on activity profiles
- **Parallel execution**: Optional Ray parallelization for performance
- **End-of-day tasks**: Follow evaluation, churn, new agent recruitment

## Example 1: Generic Simulation (Mock/Demo)

**File:** `examples/simulation_pipeline_example.py`

### Purpose
Demonstrates the simulation pattern with mocked LLM calls. Useful for understanding the structure without requiring backend services.

### Features
- ✅ Mock agent actions (no actual LLM or backend calls)
- ✅ Demonstrates parallelization pattern
- ✅ Configurable via command-line
- ✅ Works without any services running

### Usage
```bash
# Run basic simulation
python examples/simulation_pipeline_example.py --days 2 --slots 4 --agents 10

# With Ray parallelization
python examples/simulation_pipeline_example.py --days 2 --slots 4 --agents 10 --ray-cpus 4

# Full week simulation
python examples/simulation_pipeline_example.py --days 7 --slots 24 --agents 100 --pages 10
```

### When to Use
- Learning the simulation structure
- Testing without backend dependencies
- Developing new simulation features
- Quick prototyping

---

## Example 2: FakeAgent Simulation (No LLM)

**File:** `examples/simulation_pipeline_fakeagent.py`

### Purpose
Production-ready simulation using FakeAgents that connect to YServer but don't require LLM inference. Ideal for testing and development.

### Requirements
- YServer running at `http://0.0.0.0:5010` (configurable)
- Dependencies: `numpy`, `requests`, `pyautogen==0.2.31`
- Optional: `ray` for parallelization

### Features
- ✅ Real YServer connection
- ✅ FakeAgent class (simplified agent behavior)
- ✅ No LLM overhead (faster execution)
- ✅ Full simulation pipeline
- ✅ Ray parallelization support (CPU-only)

### Configuration
```bash
# Default: connects to 0.0.0.0:5010
python examples/simulation_pipeline_fakeagent.py --days 2 --slots 4 --agents 10

# Custom server
python examples/simulation_pipeline_fakeagent.py \
  --days 2 --slots 4 --agents 10 \
  --server-host 127.0.0.1 \
  --server-port 5010

# With Ray parallelization (4 CPUs)
python examples/simulation_pipeline_fakeagent.py \
  --days 2 --slots 4 --agents 10 \
  --ray-cpus 4

# Large-scale simulation
python examples/simulation_pipeline_fakeagent.py \
  --days 7 --slots 24 --agents 100 --pages 10 \
  --ray-cpus 8
```

### Command-Line Arguments
- `--days N` - Number of simulation days (default: 2)
- `--slots N` - Time slots per day (default: 4, typically 24 for full day)
- `--agents N` - Number of user agents (default: 10)
- `--pages N` - Number of page agents (default: 2)
- `--server-host HOST` - YServer host (default: 0.0.0.0)
- `--server-port PORT` - YServer port (default: 5010)
- `--ray-cpus N` - CPUs for Ray (default: 4)
- `--ray-gpus N` - GPUs for Ray (default: 0)
- `--no-ray` - Disable Ray parallelization

### When to Use
- Testing with real backend
- Development without LLM costs
- Performance benchmarking
- Large-scale simulations (faster than LLM)
- CI/CD testing pipelines

### Performance
- **Speed**: Fast (no LLM inference)
- **Resources**: CPU-only
- **Scale**: Can handle 100+ agents easily

---

## Example 3: LLM Agent Simulation (Ollama)

**File:** `examples/simulation_pipeline_llm_ollama.py`

### Purpose
Production-ready simulation using real Agent instances with LLM-powered content generation and decision-making via localhost Ollama instance.

### Requirements
- **Ollama** running at `http://127.0.0.1:11434` with llama3.2 model
- **YServer** running at `http://0.0.0.0:5010` (configurable)
- Dependencies: `numpy`, `requests`, `pyautogen==0.2.31`
- Optional: `ray` for GPU-accelerated parallelization
- Optional: GPU for faster LLM inference

### Ollama Setup
```bash
# 1. Install Ollama from https://ollama.ai/

# 2. Pull llama3.2 model
ollama pull llama3.2

# 3. Verify Ollama is running
curl http://127.0.0.1:11434/v1/models

# Ollama should start automatically and be available at:
# http://127.0.0.1:11434
```

### Features
- ✅ Real YServer connection
- ✅ Real Agent class with full LLM integration
- ✅ LLM-powered content generation (via llama3.2)
- ✅ LLM-driven decision making
- ✅ Realistic agent behavior
- ✅ Ray parallelization with GPU support
- ✅ Fractional GPU allocation (10 agents per GPU)

### Configuration
```bash
# Basic LLM simulation
python examples/simulation_pipeline_llm_ollama.py \
  --days 2 --slots 4 --agents 10

# With GPU acceleration (recommended for LLM)
python examples/simulation_pipeline_llm_ollama.py \
  --days 2 --slots 4 --agents 10 \
  --ray-gpus 1

# Custom server endpoints
python examples/simulation_pipeline_llm_ollama.py \
  --days 2 --slots 4 --agents 10 \
  --yserver-host 0.0.0.0 \
  --yserver-port 5010 \
  --ollama-url http://127.0.0.1:11434/v1 \
  --ray-gpus 1

# Large-scale LLM simulation
python examples/simulation_pipeline_llm_ollama.py \
  --days 7 --slots 24 --agents 50 --pages 5 \
  --ray-cpus 8 --ray-gpus 2
```

### Command-Line Arguments
- `--days N` - Number of simulation days (default: 2)
- `--slots N` - Time slots per day (default: 4, typically 24 for full day)
- `--agents N` - Number of user agents (default: 10)
- `--pages N` - Number of page agents (default: 2)
- `--yserver-host HOST` - YServer host (default: 0.0.0.0)
- `--yserver-port PORT` - YServer port (default: 5010)
- `--ollama-url URL` - Ollama API endpoint (default: http://127.0.0.1:11434/v1)
- `--ray-cpus N` - CPUs for Ray (default: 4)
- `--ray-gpus N` - GPUs for Ray (default: 0, use 1+ if available)
- `--no-ray` - Disable Ray parallelization

### GPU Usage
When using Ray with GPU:
- Individual tasks use fractional GPU allocation (0.1 per task)
- This allows ~10 agents to share a single GPU efficiently
- Multiple GPUs can be used for larger simulations
- Example: `--ray-gpus 2` with 50 agents = ~25 agents per GPU

### When to Use
- Production simulations requiring realistic behavior
- Research requiring LLM-generated content
- Testing LLM-driven agent interactions
- Realistic social network simulations
- Content quality evaluation

### Performance
- **Speed**: Slower (LLM inference overhead)
- **Resources**: CPU + GPU (recommended)
- **Scale**: 10-50 agents per GPU recommended
- **Quality**: High (realistic LLM-generated content)

---

## Comparison Table

| Feature | Generic (Mock) | FakeAgent | LLM Ollama |
|---------|---------------|-----------|------------|
| **YServer Required** | ❌ No | ✅ Yes | ✅ Yes |
| **LLM Required** | ❌ No | ❌ No | ✅ Yes (Ollama) |
| **Content Generation** | Mock | Simple | LLM-powered |
| **Decision Making** | Random | Simplified | LLM-driven |
| **GPU Needed** | ❌ No | ❌ No | ⚠️ Optional (recommended) |
| **Speed** | Fast | Fast | Slower |
| **Realism** | Low | Medium | High |
| **Setup Complexity** | None | Easy | Moderate |
| **Use Case** | Learning, Demo | Testing, Dev | Production, Research |
| **Ray Parallelization** | ✅ Demo only | ✅ CPU-based | ✅ GPU-accelerated |

---

## Getting Started

### Quick Start (No Services Required)
```bash
# Install dependencies
pip install numpy requests pyautogen==0.2.31

# Run generic example (no services needed)
python examples/simulation_pipeline_example.py --days 2 --slots 4 --agents 10
```

### Testing with YServer (No LLM)
```bash
# 1. Start YServer at 0.0.0.0:5010

# 2. Run FakeAgent simulation
python examples/simulation_pipeline_fakeagent.py --days 2 --slots 4 --agents 10
```

### Full LLM Simulation
```bash
# 1. Install and start Ollama
ollama pull llama3.2

# 2. Start YServer at 0.0.0.0:5010

# 3. Run LLM simulation
python examples/simulation_pipeline_llm_ollama.py --days 2 --slots 4 --agents 10
```

---

## Advanced Usage

### Ray Parallelization

All examples support Ray for parallel execution:

```bash
# Install Ray
pip install ray

# CPU-only parallelization (FakeAgent)
python examples/simulation_pipeline_fakeagent.py \
  --days 2 --slots 4 --agents 50 \
  --ray-cpus 8

# GPU-accelerated parallelization (LLM)
python examples/simulation_pipeline_llm_ollama.py \
  --days 2 --slots 4 --agents 50 \
  --ray-cpus 8 --ray-gpus 2
```

### Performance Optimization

**For FakeAgent simulations:**
- Use more CPUs: `--ray-cpus 8`
- Increase agent count: `--agents 100`
- No GPU needed

**For LLM simulations:**
- Use GPU: `--ray-gpus 1` (or more)
- Limit agents per GPU: ~10 agents per GPU
- Use fractional GPU allocation (automatic)
- More CPUs help with preprocessing: `--ray-cpus 8`

### Custom Configuration

**FakeAgent with custom server:**
```bash
python examples/simulation_pipeline_fakeagent.py \
  --days 7 --slots 24 --agents 100 --pages 10 \
  --server-host 192.168.1.100 \
  --server-port 8080 \
  --ray-cpus 16
```

**LLM with custom endpoints:**
```bash
python examples/simulation_pipeline_llm_ollama.py \
  --days 7 --slots 24 --agents 50 --pages 5 \
  --yserver-host 192.168.1.100 \
  --yserver-port 8080 \
  --ollama-url http://192.168.1.200:11434/v1 \
  --ray-cpus 8 --ray-gpus 2
```

---

## Troubleshooting

### Common Issues

**"Ray is not installed"**
- Solution: `pip install ray`
- Simulation will run sequentially without Ray

**"Resource quantities must all be whole numbers" (GPU)**
- Solution: Use whole numbers for `--ray-gpus` (0, 1, 2, not 0.5)
- Fractional GPU is only for individual tasks, not Ray init

**"Connection refused" (YServer)**
- Solution: Ensure YServer is running at specified host:port
- Check with: `curl http://0.0.0.0:5010/health` (if endpoint exists)

**"Ollama not responding"**
- Solution: Check Ollama is running: `curl http://127.0.0.1:11434/v1/models`
- Restart Ollama if needed
- Verify llama3.2 model is pulled: `ollama list`

**Slow LLM performance**
- Solution: Use GPU with `--ray-gpus 1`
- Reduce number of agents
- Use FakeAgent example for faster testing

---

## Next Steps

1. **Start Simple**: Run the generic example first to understand the structure
2. **Add Backend**: Use FakeAgent example with YServer for testing
3. **Enable LLM**: Use Ollama example for realistic simulations
4. **Scale Up**: Use Ray parallelization for larger simulations
5. **Customize**: Modify examples for your specific use case

For more information, see:
- `docs/DATA_CLASSES_AND_RAY.md` - Ray parallelization guide
- `docs/REFACTORING_GUIDE.md` - Technical reference
- `docs/MIGRATION_CHECKLIST.md` - Migration from old architecture
