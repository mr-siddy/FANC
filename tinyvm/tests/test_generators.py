from tinyvm.generators import GenSpec, ShapingSpec


def test_shaping_spec_defaults_off():
    s = ShapingSpec()
    assert s.flat_output_histogram is False
    assert s.distractor_regs == 0
    assert s.randomize_print_target is False
    assert s.decorrelate_length is False


def test_gen_spec_holds_axis_dials_and_shaping():
    s = GenSpec(
        n=16, k=4, b=2, l=8, use_stack=True, stack_frames=1,
        shaping=ShapingSpec(distractor_regs=2),
    )
    assert s.n == 16 and s.k == 4 and s.b == 2 and s.l == 8
    assert s.use_stack is True and s.stack_frames == 1
    assert s.shaping.distractor_regs == 2
