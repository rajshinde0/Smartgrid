Twelve slides, **headline first**. The rule throughout: one idea per slide, the
number on the slide, the caveat spoken aloud.

**1. Title and the one-sentence finding** SMARTGRID-X. *"Seven buildings on a
real campus draw 62%-85% of their average power when they are at their
emptiest."* Give the finding before the method. Everything after this slide is
evidence for it.

**2. The problem and the data** Buildings use power when nobody is there;
measuring it needs energy data *and* occupancy data together. I-BLEND has both:
1-minute meters on 7 IIIT-Delhi buildings plus WiFi device counts, Feb 2014 -
Nov 2017. *Figure:* `fig_00_coverage_timeline.png`.

**3. The problem we hit immediately** Occupancy never reads zero -- minimum is 1
in every building, because idle phones stay connected. So "empty" is not
measurable and the question had to be re-specified around a **relative**
low-occupancy threshold, published with a sensitivity curve. *This slide is
where the examiner learns we read our own data.*

**4. Cleaning: what we found and what we did** 81.7% of Lecture readings are
exactly 0 W (dead meter, not an idle building). Negative power factor on up to
66% of rows is a sign convention, not corruption -- dropping it would have
destroyed 58% of the Library record. *Figure:* `fig_01_missing_heatmap.png`.

**5. What a normal day looks like** *Figure:* `fig_02_hourly_profile_all.png`.
Academic peaks at 41 kW and still draws about 20 kW at 3 a.m. Hostels do the
opposite. Facilities is nearly flat -- its consumption barely knows what time it
is.

**6. THE HEADLINE** *Figure:* `fig_05_headline.png`. Give the intensity ratio,
not just the share: "Lecture draws 85% of its average power when nearly empty;
Library, the best on campus, still draws 62%."

**7. Is the headline robust?** *Figure:* `fig_05_sensitivity_curve.png`. The
threshold is a judgement, so here is every other threshold. Rankings do not
move. Also: the base load computed two independent ways agrees.

**8. Does it match anyone else?** *Figure:* `fig_05_published_comparison.png`.
Applying Masoso & Grobler's own clock-based definition to our data gives 55.2%
and 55.0% against their published 56%. Different continent, fifteen years apart.
**This is the credibility slide.**

**9. Can we predict it? (RQ2)** Occupancy adds only +0.107 to validation
R-squared. Say the negative result plainly -- it matches published work, and
three different analyses in this project reached it independently. *Figure:*
`fig_04_model_comparison.png`.

**10. Can we detect it automatically? (RQ3)** The experiment: two detectors,
synthetic labelled anomalies, seed 42. **Say "synthetic" out loud.** Result:
occupancy helps consistently but by only 1-3 points, and most on the waste
anomalies. Mention the trap we caught -- the planned fixed threshold was not a
fair comparison. *Figure:* `fig_06_detector_comparison.png`.

**11. Limitations, said before anyone asks** No weather data (Delhi's vacation
is its hottest season, so some of this is cooling an empty building). WiFi
counts devices, not people -- which makes our numbers a *lower* bound. Injected
anomalies are synthetic. Lecture has only 19% usable data. One campus, one
climate.

**12. So what, and a live dashboard** The opportunity is the **fixed** part of
the load: this is a controls and commissioning problem, not a sensing problem.
The Library proves it can be done. Then demonstrate `streamlit run
dashboard/app.py` -- pick a building, pick a week, show the flagged periods.

**If asked "what is new here?"** -- *"The methods are standard. What we could
not find published is anyone using I-BLEND's own occupancy stream to quantify,
per building, how much of the campus's electricity is used while it is nearly
empty, with a threshold-sensitivity curve and a controlled test of whether
occupancy helps a detector."*

**If asked about the null results** -- *"Two of our three questions came back
weaker than we hoped. We report them because they agree with published work and
because three independent analyses in this project reached the same conclusion.
The main finding does not depend on them."*