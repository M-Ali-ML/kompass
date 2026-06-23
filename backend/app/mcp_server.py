from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MathServer")

@mcp.tool()
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers.

    Args:
        a: The first integer.
        b: The second integer.
    """
    return a + b

if __name__ == "__main__":
    mcp.run()
