from flask import Blueprint, request, jsonify

# Define the blueprint
bp = Blueprint("main", __name__)


# Route: Home Page
@bp.route("/")
def home():
    return jsonify({"message": "Hello there!"})


# Route: POST /papers (Create a new paper - placeholder)
@bp.route("/papers", methods=["POST"])
def create_paper():
    # In a real application, you'd process the request data (e.g., from a JSON body)
    # and save the paper to a database.  For now, we just return an empty object.
    # TODO: request.form.get("file")
    return jsonify({}), 201  # 201 Created


# Route: GET /papers (List papers, optionally with a query)
@bp.route("/papers", methods=["GET"])
def list_papers():
    query = request.args.get("query")  # Get the 'query' parameter from the URL

    # In a real application, you'd fetch papers from a database,
    # potentially filtering based on the 'query' parameter.
    # For now, we return an empty list.
    if query:
        # Placeholder for filtered results.  In a real app, you'd query a database.
        return jsonify([])
    else:
        return jsonify([])


# Route: GET /papers/<id> (Get a specific paper by ID)
@bp.route("/papers/<string:id>", methods=["GET"])  # Ensure 'id' is treated as an integer
def get_paper(id):
    # In a real application, you'd fetch the paper with the given ID from a database.
    # For now, we return an empty object.
    return jsonify({})
