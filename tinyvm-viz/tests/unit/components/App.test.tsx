import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

describe("App shell", () => {
  it("renders the Playground at /", () => {
    render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
    expect(screen.getByText(/Counter/)).toBeInTheDocument();
  });

  it("renders the Compare page at /compare", () => {
    render(<MemoryRouter initialEntries={["/compare"]}><App /></MemoryRouter>);
    expect(screen.getByText(/Comparison view/)).toBeInTheDocument();
  });
});
