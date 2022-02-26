
clean-iac:
	rm -f iac/views/build/*.yaml; \
	rm -f iac/procedures/build/*.yaml; \
	rm -f iac/tables/build/*.json; \
	rm -f iac/schedueled_queries/build/*.yaml; \
	rm -frd iac/functions/make_predictions/__pycache__; \
	rm -frd iac/functions/make_predictions/htmlcov
	rm -f iac/functions/make_predictions/.coverage

prepare-iac:
	cd tools; \
	sh generate_iac.sh; \

plan : clean-iac prepare-iac
	cd iac; \
	tfsec; \
	terraform plan;

deploy : plan
	cd iac && terraform apply -auto-approve

run-tests:
	cd iac/functions/make_predictions; \
	coverage run --source=. binancebot_test.py ; \
	coverage report; \
	coverage html;