# Obelisk Virtual Try-On Makefile
SHELL := /bin/bash
.PHONY: help install dev build clean frontend-install frontend-dev frontend-build api-dev test

help:
	@echo "Available commands:"
	@echo "  make install         - Install all dependencies (frontend + backend)"
	@echo "  make dev            - Run both frontend and backend in development mode"
	@echo "  make build          - Build frontend for production"
	@echo "  make clean          - Clean build artifacts and dependencies"
	@echo "  make frontend-install - Install frontend dependencies"
	@echo "  make frontend-dev   - Run frontend development server"
	@echo "  make frontend-build - Build frontend for production"
	@echo "  make api-dev        - Run backend API server"
	@echo "  make test           - Run tests"

install: frontend-install
	@echo "Installing backend dependencies..."
	@pip install poetry
	@poetry install

frontend-install:
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install

dev:
	@echo "Starting development servers..."
	@make -j 2 frontend-dev adk-dev

frontend-dev:
	@echo "Starting frontend development server..."
	@cd frontend && npm run dev

api-dev:
	@echo "Starting API server..."
	@poetry run python mock_api.py 

adk-dev:
	@echo "Starting ADK API server..."
	@poetry run adk api_server .

build: frontend-build
	@echo "Build complete!"

frontend-build:
	@echo "Building frontend..."
	@cd frontend && npm run build

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf frontend/dist
	@rm -rf frontend/node_modules
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean complete!"

test:
	@echo "Running tests..."
	@poetry run pytest tests/
	@cd frontend && npm run lint