<script>
function enablePopOvers() { 
  $('.reference_number').each( function(index, E) {
    var target = document.getElementById($(E).attr('href').slice(1));
    var target_type = str(target.attributes['type']);
    var target_number = str(target.attributes['id']);
    var target_content = ""
    $(target.children).not('.block_heading').each(function() {
      target_content += $(this).html();
    });
    var title = "<span class='block_heading "+target_type"'>"+
            "<span class='block_number'>"+target_number+"</span>"+
	    "</span>";
    jqE = $(E)
    jqE.attr('data-content',target_content);
    jqE.attr('data-html',true);
    jqE.attr('data-trigger','hover');
    jqE.attr('data-title',title)
  });
}

function hideTOC() { 
  $('#toc').hide('slow');
  return true;
}

function showTOC() {
  $('#toc').show('slow');   
  return true;
}

jQuery(document).ready( function () {
  //alert('Will call MathJaX QUEUE');
  MathJax.Hub.Queue(function() { 
    //alert('Calling Queued Function');
    addTwipsyLinks();
  });
})
</script>