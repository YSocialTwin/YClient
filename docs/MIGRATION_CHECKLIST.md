# Migration Checklist: Data Classes and Ray Parallelization

Use this checklist to track your migration to the new data class architecture with Ray parallelization.

## Pre-Migration

- [ ] Read [DATA_CLASSES_AND_RAY.md](DATA_CLASSES_AND_RAY.md) for overview
- [ ] Read [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md) for details
- [ ] Review [ray_parallel_example.py](../examples/ray_parallel_example.py)
- [ ] Backup your current simulation data
- [ ] Ensure you have Python 3.8+ installed

## Installation

- [ ] Update code from repository
- [ ] Install new dependencies:
  ```bash
  pip install -r requirements_client.txt
  ```
- [ ] Verify Ray installation:
  ```python
  python -c "import ray; print('Ray version:', ray.__version__)"
  ```
- [ ] Test new imports:
  ```python
  from y_client.classes.agent_data import AgentData
  from y_client.functions import post_content
  from y_client.functions.ray_integration import init_ray
  print("✓ All new modules available")
  ```

## Choose Migration Path

Select ONE of the following approaches:

### Option A: Gradual Migration (Recommended)
- [ ] Keep using existing Agent classes
- [ ] Identify performance bottlenecks
- [ ] Add Ray parallelization to bottlenecks only
- [ ] Convert Agents to AgentData for parallel operations
- [ ] No changes to existing simulation code needed

**Implementation:**
```python
# Existing code works as-is
agent = Agent(...)
agent.post(tid=1)

# Add parallelization where needed
agent_data_list = [agent_to_data(a) for a in agents]
execute_parallel_gpu('post_content', agent_data_list, tid=1)
```

### Option B: Full Migration
- [ ] Replace all Agent instantiations with AgentData
- [ ] Replace all agent.method() calls with function(agent_data) calls
- [ ] Update all agent storage/retrieval code
- [ ] Update client code to work with AgentData
- [ ] Enable Ray for all operations

**Implementation:**
```python
# Replace this:
agent = Agent(name="user1", ...)
agent.post(tid=1)

# With this:
agent_data = AgentData(name="user1", ...)
post_content(agent_data, tid=1)
```

### Option C: Wrapper Approach
- [ ] Replace Agent instantiations with wrapped AgentData
- [ ] Minimal code changes required
- [ ] Optionally enable Ray
- [ ] Gradual refactoring possible

**Implementation:**
```python
# Replace this:
agent = Agent(name="user1", ...)

# With this:
agent_data = AgentData(name="user1", ...)
agent = wrap_agent_data(agent_data, use_ray=True)

# No other changes - use agent as before
agent.post(tid=1)
```

## Testing

- [ ] Run simulation without Ray (verify functionality)
  ```python
  # Test basic operations
  agent_data = AgentData(name="test", email="test@test.com", ...)
  # Verify all operations work
  ```

- [ ] Initialize Ray and verify resources
  ```python
  from y_client.functions.ray_integration import init_ray
  init_ray()
  # Check output for available CPUs/GPUs
  ```

- [ ] Test CPU parallelization
  ```python
  results = execute_parallel_cpu('read_posts', agent_data_list)
  # Verify results match sequential execution
  ```

- [ ] Test GPU parallelization
  ```python
  results = execute_parallel_gpu('post_content', agent_data_list, tid=1)
  # Verify posts are created correctly
  ```

- [ ] Benchmark performance improvement
  ```python
  # Measure sequential time
  # Measure parallel time
  # Calculate speedup
  ```

## Production Deployment

- [ ] Configure Ray for your hardware
  ```python
  init_ray(
      num_cpus=8,      # Match your CPU cores
      num_gpus=2,      # Match your GPUs
  )
  ```

- [ ] Set up monitoring
  - [ ] Ray dashboard (http://localhost:8265)
  - [ ] Resource utilization tracking
  - [ ] Performance metrics logging

- [ ] Update deployment scripts
  - [ ] Add Ray initialization
  - [ ] Configure resource allocation
  - [ ] Add cleanup/shutdown

- [ ] Document configuration
  - [ ] Record optimal CPU/GPU settings
  - [ ] Document batch sizes
  - [ ] Note any custom configurations

## Optimization

- [ ] Profile your simulation
  - [ ] Identify bottlenecks
  - [ ] Measure operation times
  - [ ] Track resource usage

- [ ] Tune batch sizes
  - [ ] Test different batch sizes for parallel operations
  - [ ] Find optimal balance between parallelism and overhead
  - [ ] Document optimal values

- [ ] Optimize GPU allocation
  - [ ] Adjust `num_gpus` parameter in remote functions
  - [ ] Test different fractional GPU values (0.05, 0.1, 0.2)
  - [ ] Find optimal GPU sharing ratio

- [ ] Consider distributed setup (if applicable)
  - [ ] Set up Ray cluster across machines
  - [ ] Configure head and worker nodes
  - [ ] Test distributed execution

## Validation

- [ ] Compare outputs
  - [ ] Run same simulation with old and new code
  - [ ] Verify agent behaviors are identical
  - [ ] Check post content quality

- [ ] Verify data integrity
  - [ ] Ensure all agent data is preserved
  - [ ] Check database consistency
  - [ ] Validate serialization/deserialization

- [ ] Performance validation
  - [ ] Confirm expected speedup
  - [ ] Verify memory reduction
  - [ ] Check resource utilization

## Documentation

- [ ] Update internal documentation
- [ ] Document your migration experience
- [ ] Share findings with team
- [ ] Report any issues found

## Common Issues and Solutions

### Issue: Ray not found
**Solution:**
```bash
pip install ray
```

### Issue: Out of memory
**Solution:**
- Reduce batch size
- Process agents in smaller groups
- Increase system RAM or use distributed setup

### Issue: GPU not detected
**Solution:**
- Check CUDA installation: `nvidia-smi`
- Verify PyTorch CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
- Ray will fall back to CPU if no GPU

### Issue: Import errors with AgentData
**Solution:**
- Import directly from module:
  ```python
  from y_client.classes.agent_data import AgentData
  ```
- Don't import from y_client.classes if there are dependency issues

### Issue: Slower performance than expected
**Solution:**
- Check Ray dashboard for resource bottlenecks
- Increase batch size for parallel operations
- Verify GPU utilization
- Ensure Ray is actually being used

## Success Criteria

Mark these when achieved:

- [ ] Simulation runs successfully with new architecture
- [ ] Performance improvement of 2x or more
- [ ] Memory usage reduced by 50% or more
- [ ] No data loss or corruption
- [ ] Team is comfortable with new approach
- [ ] Documentation is complete

## Rollback Plan

If migration fails:

- [ ] Document issues encountered
- [ ] Restore from backup
- [ ] Revert to legacy Agent classes
- [ ] Report issues on GitHub
- [ ] Plan retry with lessons learned

## Post-Migration

- [ ] Monitor production performance
- [ ] Collect metrics and feedback
- [ ] Optimize based on real usage
- [ ] Share success story
- [ ] Contribute improvements back

## Resources

- [DATA_CLASSES_AND_RAY.md](DATA_CLASSES_AND_RAY.md) - Quick start guide
- [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md) - Detailed documentation
- [ray_parallel_example.py](../examples/ray_parallel_example.py) - Code examples
- [Ray Documentation](https://docs.ray.io/) - Official Ray docs

## Support

Need help? 

1. Check example code in `examples/ray_parallel_example.py`
2. Review documentation in `docs/`
3. Search existing GitHub issues
4. Open a new issue with:
   - Migration path chosen
   - Error messages
   - System specifications
   - Steps to reproduce

---

**Good luck with your migration!** 🚀

The new architecture will make your simulations faster, more efficient, and more scalable.
