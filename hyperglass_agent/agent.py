# Standard Library Imports
import json
from pathlib import Path

# Third Party Imports
import responder
from logzero import logger as log
from pydantic import ValidationError

# Project Imports
from hyperglass_agent.config import params
from hyperglass_agent.exceptions import HyperglassAgentError
from hyperglass_agent.execute import run_query
from hyperglass_agent.payload import jwt_encode, jwt_decode
from hyperglass_agent.models.request import Request

LOG_LEVEL = "info"
if params.debug:
    LOG_LEVEL = "debug"

WORKING_DIR = Path(__file__).parent

CERT_FILE = WORKING_DIR / "agent_cert.pem"
KEY_FILE = WORKING_DIR / "agent_key.pem"

api = responder.API()


@api.route("/query")
async def query_entrypoint(req, resp):

    try:
        query = await req.media()
        log.debug(f"Raw Query JSON: {query}")

        query_str = query["encoded"]
        decrypted_query = await jwt_decode(query_str)
        decrypted_query = json.loads(decrypted_query)

        log.debug(decrypted_query)

        validated_query = Request(**decrypted_query)
        query_output = await run_query(validated_query)
        resp.media = await jwt_encode(query_output)

    except ValidationError as err_validation:
        resp.status_code = 400
        resp.media = {"error": str(err_validation)}

    except HyperglassAgentError as err_agent:
        resp.status_code = err_agent.code
        resp.media = {"error": str(err_agent)}


if __name__ == "__main__":
    api.run(
        address=params.listen_address.compressed,
        port=params.port,
        log_level=LOG_LEVEL,
        debug=params.debug,
        ssl_keyfile=KEY_FILE,
        ssl_certfile=CERT_FILE,
    )
