# Hesperia repo — convenience targets (T52)
.PHONY: output-views-test output-views-golden output-views-inspector-fixture
output-views-test:
	cd output_views && python3 manage.py test apps.pages

output-views-golden:
	cd output_views && python3 scripts/validate_golden_segment.py verify

output-views-inspector-fixture:
	cd output_views && python3 scripts/generate_inspector_fixture.py --from-ci-bundle
