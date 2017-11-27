$(document).ready( function() {

    $("#search").addEventListener("keyup", function(event) {
        var value = $(this).val();
        $.ajax({
            url: "http://search.xignite.com/Search/Suggest?parameter=XigniteFinancials.GetCompanyBalanceSheet.Identifier&term=" + value + "&tags=XNYS,XNAS",
            success: function(responses) {
                console.log(responses);
                $("#searchresults").empty();
                for (var i = 0; i < responses.Results.length; i++) {
                    //console.log(responses.Results[i].Value);
                    $("<option/>").html(responses.Results[i].Value).appendTo("#searchresults");
                }
                $(this).focus();
            }
        
        });
    }, false);

} );

